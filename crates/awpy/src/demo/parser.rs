use std::path::Path;

use memmap2::Mmap;
use pbdems2::{ParserState, PreparedPlayback};
use prost::Message;

use crate::error::{Error, Result};
use crate::io::{BitReader, ByteReader};
use crate::lazy::LazyCache;

use std::collections::HashMap;
use std::sync::Arc;

use super::command::{self, CmdHeader, dem, ge, net, svc};

use super::adapter::Cs2Adapter;
use super::events::{
    EventDescriptor, decode_direct_user_message, decode_legacy_event, decode_user_message,
};

mod playback;

pub use playback::Segment;
pub(crate) use playback::segment_budget;

use awpy_proto::proto::{
    CDemoFileHeader, CDemoFileInfo, CDemoFullPacket, CDemoPacket, CMsgSource1LegacyGameEventList,
    CnetMsgSetConVar,
};

/// Magic bytes at the start of every Source 2 demo file.
const MAGIC: &[u8; 8] = b"PBDEMS2\0";
/// File header: 8 bytes magic + 4 bytes fileinfo_offset + 4 bytes spawngroups_offset.
const HEADER_SIZE: usize = 16;

/// Fallback tick interval used before server information is available.
const DEFAULT_TICK_INTERVAL: f32 = 1.0 / 64.0;

/// Scratch buffer size for decompressed command bodies and packet payloads.
const BUF_SIZE: usize = 2 * 1024 * 1024;
/// Initial capacity for relevant inner-message payloads. The buffer grows for
/// unusually large messages instead of zeroing 2 MiB for every parse worker.
const PACKET_BUF_CAPACITY: usize = 64 * 1024;

/// Information about a demo message in the command stream.
#[derive(Debug, Clone, serde::Serialize)]
pub struct MessageInfo {
    /// Zero-based ordinal position in the command stream.
    pub index: usize,
    /// Command type (one of the `dem::*` constants).
    pub cmd: i32,
    /// Human-readable command name.
    pub cmd_name: String,
    /// Game tick this command applies to.
    pub tick: i32,
    /// Whether the body is Snappy-compressed.
    pub compressed: bool,
    /// Body size in bytes (before decompression).
    pub body_size: u32,
    /// Absolute byte offset from the start of the file.
    pub offset: usize,
}

/// Full parser context after initialization.
///
/// Holds all decoded game state: serializers, class definitions, string
/// tables, and live entities. Returned by [`Parser::parse_init`],
/// [`Parser::parse_to_tick`], and updated incrementally during
/// [`Parser::run_to_end`].
pub type Context = ParserState;

/// A game event extracted from the demo.
#[derive(Debug, Clone, serde::Serialize)]
pub struct GameEvent {
    /// Game tick at which this event occurred.
    pub tick: i32,
    /// Human-readable event name (e.g. `"player_death"`, `"CS_UM_SayText2"`).
    pub name: String,
    /// Numeric message type from the packet stream.
    pub msg_type: u32,
    /// Key-value pairs for Source 1 legacy game events; empty for user messages.
    pub keys: Vec<(String, String)>,
    /// Raw protobuf bytes of the event. Use [`crate::decode_event_payload`] to decode.
    #[serde(skip)]
    pub payload: Vec<u8>,
}

/// Internal storage for demo data — either memory-mapped or an owned byte buffer.
enum Storage {
    Mmap(Mmap),
    Bytes(Vec<u8>),
}

impl AsRef<[u8]> for Storage {
    fn as_ref(&self) -> &[u8] {
        match self {
            Storage::Mmap(m) => m,
            Storage::Bytes(b) => b,
        }
    }
}

/// The main parser. Owns the demo file data (memory-mapped or in-memory).
pub struct Parser {
    storage: Storage,
    /// Raw game events, decoded once for the generic event API.
    /// Enriched combat datasets use their own selected-event playback.
    events_cache: LazyCache<Arc<[GameEvent]>>,
    /// Signon state is expensive to decode but immutable between parse passes.
    prepared_cache: LazyCache<PreparedPlayback<Cs2Adapter>>,
    combat_bootstrap: LazyCache<playback::CombatBootstrap>,
    file_header_cache: LazyCache<CDemoFileHeader>,
    file_info_cache: LazyCache<CDemoFileInfo>,
}

impl Parser {
    fn new(storage: Storage) -> Self {
        Self {
            storage,
            events_cache: LazyCache::default(),
            prepared_cache: LazyCache::default(),
            combat_bootstrap: LazyCache::default(),
            file_header_cache: LazyCache::default(),
            file_info_cache: LazyCache::default(),
        }
    }

    /// Open a demo file and map its bytes into memory.
    ///
    /// The file must not change while the parser exists.
    ///
    /// # Errors
    ///
    /// Returns an error if the file cannot be opened or mapped.
    pub fn from_file(path: &Path) -> Result<Self> {
        let file = std::fs::File::open(path)?;
        // SAFETY: The file is opened read-only and the mapping lives as
        // long as the Parser.  Undefined behavior can occur if an external
        // process truncates or modifies the file while mapped; callers must
        // ensure the file is not concurrently mutated.
        let mmap = unsafe { Mmap::map(&file)? };
        Ok(Self::new(Storage::Mmap(mmap)))
    }

    /// Create a parser from an in-memory byte buffer.
    ///
    /// This is useful for testing, WASM targets (where mmap is unavailable),
    /// or when the demo data has already been loaded into memory.
    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        Self::new(Storage::Bytes(bytes))
    }

    /// Returns the raw demo data.
    fn data(&self) -> &[u8] {
        self.storage.as_ref()
    }

    /// Verify that the file has valid demo magic bytes.
    pub fn verify(&self) -> Result<()> {
        if self.data().len() < HEADER_SIZE {
            return Err(Error::Parse {
                context: "file too small for demo header".into(),
            });
        }

        let mut magic = [0u8; 8];
        magic.copy_from_slice(&self.data()[0..8]);
        if &magic != MAGIC {
            return Err(Error::InvalidMagic { got: magic });
        }

        Ok(())
    }

    fn read_cmd_header(reader: &mut ByteReader) -> Result<CmdHeader> {
        let raw_cmd = reader.read_uvarint32()?;
        // Fields are read in stream order: command, tick, body size.
        Ok(CmdHeader {
            cmd: (raw_cmd & !dem::IS_COMPRESSED) as i32,
            compressed: raw_cmd & dem::IS_COMPRESSED != 0,
            tick: reader.read_uvarint32()? as i32,
            body_size: reader.read_uvarint32()?,
        })
    }

    /// Read and decompress a command body into the provided buffer.
    /// The buffer is resized as needed and can be reused across calls.
    fn read_cmd_body(reader: &mut ByteReader, header: &CmdHeader, buf: &mut Vec<u8>) -> Result<()> {
        let raw = reader.read_bytes(header.body_size as usize)?;
        buf.clear();
        if header.compressed {
            buf.resize(snap::raw::decompress_len(raw)?, 0);
            snap::raw::Decoder::new().decompress(raw, buf)?;
        } else {
            buf.extend_from_slice(raw);
        }
        Ok(())
    }

    /// Return metadata for all commands.
    ///
    /// Continue after `DEM_Stop` to read `DEM_FileInfo`.
    pub fn messages(&self) -> Result<Vec<MessageInfo>> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut messages = Vec::new();
        let mut index = 0;

        while reader.remaining() > 0 {
            let offset = reader.position() + HEADER_SIZE;
            let header = Self::read_cmd_header(&mut reader)?;

            messages.push(MessageInfo {
                index,
                cmd: header.cmd,
                cmd_name: command::command_name(header.cmd).to_string(),
                tick: header.tick,
                compressed: header.compressed,
                body_size: header.body_size,
                offset,
            });

            // `DEM_Stop` has no body. `DEM_FileInfo` follows it.
            if header.cmd == dem::STOP {
                index += 1;
                continue;
            }

            // Stop after `DEM_FileInfo`.
            if header.cmd == dem::FILE_INFO {
                reader.skip(header.body_size as usize)?;
                break;
            }

            reader.skip(header.body_size as usize)?;

            index += 1;
        }

        Ok(messages)
    }

    /// Find and decode the CDemoFileHeader message.
    pub fn file_header(&self) -> Result<CDemoFileHeader> {
        self.file_header_cache
            .get_or_try_init(|| {
                self.verify()?;
                let mut reader = ByteReader::new(&self.data()[HEADER_SIZE..]);
                let mut body = Vec::with_capacity(BUF_SIZE);
                while reader.remaining() > 0 {
                    let header = Self::read_cmd_header(&mut reader)?;
                    match header.cmd {
                        dem::FILE_HEADER => {
                            Self::read_cmd_body(&mut reader, &header, &mut body)?;
                            return Ok(CDemoFileHeader::decode(&body[..])?);
                        }
                        dem::STOP => break,
                        _ => reader.skip(header.body_size as usize)?,
                    }
                }
                Err(Error::Parse {
                    context: "DEM_FileHeader not found".into(),
                })
            })
            .cloned()
    }

    /// Decode CDemoFileInfo using the offset stored in the file header.
    pub fn file_info(&self) -> Result<CDemoFileInfo> {
        self.file_info_cache
            .get_or_try_init(|| {
                self.verify()?;
                // Bytes 8..12 of the file header hold the absolute offset to DEM_FileInfo.
                let offset = u32::from_le_bytes(self.data()[8..12].try_into().expect("4 bytes"));
                let offset = offset as usize;
                let mut reader = ByteReader::new(&self.data()[HEADER_SIZE..]);
                reader.seek(offset.saturating_sub(HEADER_SIZE))?;
                let header = Self::read_cmd_header(&mut reader)?;
                if header.cmd != dem::FILE_INFO {
                    return Err(Error::Parse {
                        context: format!(
                            "expected DEM_FileInfo at offset {offset}, found command {}",
                            header.cmd
                        ),
                    });
                }
                let mut body = Vec::new();
                Self::read_cmd_body(&mut reader, &header, &mut body)?;
                Ok(CDemoFileInfo::decode(&body[..])?)
            })
            .cloned()
    }

    /// Decode the game-event stream: Source 1 legacy game events and user
    /// messages from every packet. Without `max_tick`, copy the cached full
    /// stream; with it, decode only the events up to that tick.
    pub fn events(&self, max_tick: Option<i32>) -> Result<Vec<GameEvent>> {
        match max_tick {
            None => Ok(self.events_ref()?.to_vec()),
            Some(_) => self.decode_events(max_tick),
        }
    }

    /// The full, cached event stream — decoded on first call, then reused.
    pub(crate) fn events_ref(&self) -> Result<&[GameEvent]> {
        Ok(self.events_shared_ref()?)
    }

    /// Share the cached full event stream without cloning its event payloads.
    ///
    /// This is useful for bindings and other long-lived consumers that need an
    /// owned handle while preserving the parser's single decoded copy.
    pub fn events_shared(&self) -> Result<Arc<[GameEvent]>> {
        self.events_shared_ref().map(Arc::clone)
    }

    fn events_shared_ref(&self) -> Result<&Arc<[GameEvent]>> {
        self.events_cache
            .get_or_try_init(|| self.decode_events(None).map(Arc::from))
    }

    /// Decode and cache the event stream now, if it isn't already, so
    /// first-use latency falls outside a timed operation.
    pub fn prime_events(&self) -> Result<()> {
        self.events_ref().map(drop)
    }

    fn decode_events(&self, max_tick: Option<i32>) -> Result<Vec<GameEvent>> {
        let mut events = Vec::new();
        let mut descriptors: HashMap<i32, EventDescriptor> = HashMap::new();
        let wanted = |msg_type| {
            matches!(
                msg_type,
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST
                    | ge::SOURCE1_LEGACY_GAME_EVENT
                    | svc::USER_MESSAGE
            ) || command::is_user_message_type(msg_type)
        };
        self.for_each_message(max_tick, wanted, |tick, msg_type, data| {
            match msg_type {
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST => {
                    let list = CMsgSource1LegacyGameEventList::decode(data)?;
                    for desc in list.descriptors {
                        descriptors.insert(desc.eventid.unwrap_or_default(), desc.into());
                    }
                }
                ge::SOURCE1_LEGACY_GAME_EVENT => {
                    events.push(decode_legacy_event(
                        tick,
                        msg_type,
                        data,
                        &descriptors,
                        true,
                    )?);
                }
                svc::USER_MESSAGE => events.push(decode_user_message(tick, data)?),
                _ => events.push(decode_direct_user_message(tick, msg_type, data)?),
            }
            Ok(())
        })?;
        Ok(events)
    }

    /// Server console variables (`net_SetConVar` messages), in stream order.
    ///
    /// Convars mostly arrive in the signon packets; when a name repeats, the
    /// later value is the one in effect.
    pub fn convars(&self) -> Result<Vec<(String, String)>> {
        let mut convars = Vec::new();
        let wanted = |msg_type| msg_type == net::SET_CON_VAR;
        self.for_each_message(None, wanted, |_, _, data| {
            let cvars = CnetMsgSetConVar::decode(data)?.convars.into_iter();
            convars.extend(cvars.flat_map(|list| list.cvars).map(|cvar| {
                (
                    cvar.name.unwrap_or_default(),
                    cvar.value.unwrap_or_default(),
                )
            }));
            Ok(())
        })?;
        Ok(convars)
    }

    /// Call `f(tick, msg_type, payload)` for every packet message that `wanted`
    /// selects, in stream order, until `DEM_Stop` or a command past `max_tick`.
    fn for_each_message(
        &self,
        max_tick: Option<i32>,
        wanted: impl Fn(u32) -> bool,
        mut f: impl FnMut(i32, u32, &[u8]) -> Result<()>,
    ) -> Result<()> {
        self.verify()?;
        let mut reader = ByteReader::new(&self.data()[HEADER_SIZE..]);
        let mut body = Vec::with_capacity(BUF_SIZE);
        let mut message = Vec::with_capacity(PACKET_BUF_CAPACITY);
        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;
            if header.cmd == dem::STOP || max_tick.is_some_and(|max| header.tick > max) {
                break;
            }
            let data = match header.cmd {
                dem::PACKET | dem::SIGNON_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body)?;
                    CDemoPacket::decode(&body[..])?.data
                }
                dem::FULL_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body)?;
                    CDemoFullPacket::decode(&body[..])?
                        .packet
                        .and_then(|p| p.data)
                }
                _ => {
                    reader.skip(header.body_size as usize)?;
                    continue;
                }
            };
            let Some(data) = data else { continue };
            let mut bits = BitReader::new(&data);
            while bits.bits_remaining() > 8 {
                let msg_type = bits.read_ubitvar()?;
                let size = bits.read_uvarint32()? as usize;
                if !wanted(msg_type) {
                    bits.skip_bits(size * 8)?;
                    continue;
                }
                if size > message.len() {
                    message.resize(size, 0);
                }
                bits.read_bytes(&mut message[..size])?;
                f(header.tick, msg_type, &message[..size])?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parser_with_truncated_command() -> Parser {
        let mut bytes = vec![0; HEADER_SIZE];
        bytes[..MAGIC.len()].copy_from_slice(MAGIC);
        bytes.push(0x80);
        Parser::from_bytes(bytes)
    }

    #[test]
    fn messages_rejects_a_truncated_command() {
        assert!(parser_with_truncated_command().messages().is_err());
    }

    #[test]
    fn events_rejects_a_truncated_command() {
        assert!(parser_with_truncated_command().events(None).is_err());
    }

    #[test]
    fn convars_rejects_a_truncated_command() {
        assert!(parser_with_truncated_command().convars().is_err());
    }
}
