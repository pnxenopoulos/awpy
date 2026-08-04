use std::path::Path;

use memmap2::Mmap;
use pbdems2::{ParserState, PreparedPlayback};
use prost::Message;

use crate::error::{Error, Result};
use crate::io::{BitReader, ByteReader};

use std::collections::HashMap;
use std::sync::{Arc, Mutex, OnceLock};

use super::command::{self, CmdHeader, dem, ge, net, svc};

use super::adapter::Cs2Adapter;

mod playback;

use awpy_proto::proto::{
    CDemoFileHeader, CDemoFileInfo, CDemoFullPacket, CDemoPacket, CMsgSource1LegacyGameEvent,
    CMsgSource1LegacyGameEventList, CnetMsgSetConVar, CsvcMsgUserMessage,
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

struct EventDescriptor {
    name: String,
    field_names: Vec<String>,
}

fn format_event_key(key: &awpy_proto::proto::c_msg_source1_legacy_game_event::KeyT) -> String {
    if let Some(ref s) = key.val_string {
        return s.clone();
    }
    if let Some(f) = key.val_float {
        return f.to_string();
    }
    if let Some(l) = key.val_long {
        return l.to_string();
    }
    if let Some(s) = key.val_short {
        return s.to_string();
    }
    if let Some(b) = key.val_byte {
        return b.to_string();
    }
    if let Some(b) = key.val_bool {
        return b.to_string();
    }
    if let Some(u) = key.val_uint64 {
        return u.to_string();
    }
    String::new()
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
    /// The fully-decoded game-event stream, decoded once on first use. Every
    /// higher-level dataset (kills, damages, bomb, ...) reads the events, so
    /// caching the decode here means the demo's event stream is walked once per
    /// `Parser`, not once per dataset.
    events_cache: OnceLock<Arc<[GameEvent]>>,
    events_lock: Mutex<()>,
    /// Signon state is expensive to decode but immutable between parse passes.
    prepared_cache: OnceLock<PreparedPlayback<Cs2Adapter>>,
    prepared_lock: Mutex<()>,
    file_header_cache: OnceLock<CDemoFileHeader>,
    file_info_cache: OnceLock<CDemoFileInfo>,
}

impl Parser {
    /// Open a demo file and memory-map it for zero-copy parsing.
    pub fn from_file(path: &Path) -> Result<Self> {
        let file = std::fs::File::open(path)?;
        // SAFETY: The file is opened read-only and the mapping lives as
        // long as the Parser.  Undefined behavior can occur if an external
        // process truncates or modifies the file while mapped; callers must
        // ensure the file is not concurrently mutated.
        let mmap = unsafe { Mmap::map(&file)? };
        Ok(Self {
            storage: Storage::Mmap(mmap),
            events_cache: OnceLock::new(),
            events_lock: Mutex::new(()),
            prepared_cache: OnceLock::new(),
            prepared_lock: Mutex::new(()),
            file_header_cache: OnceLock::new(),
            file_info_cache: OnceLock::new(),
        })
    }

    /// Create a parser from an in-memory byte buffer.
    ///
    /// This is useful for testing, WASM targets (where mmap is unavailable),
    /// or when the demo data has already been loaded into memory.
    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        Self {
            storage: Storage::Bytes(bytes),
            events_cache: OnceLock::new(),
            events_lock: Mutex::new(()),
            prepared_cache: OnceLock::new(),
            prepared_lock: Mutex::new(()),
            file_header_cache: OnceLock::new(),
            file_info_cache: OnceLock::new(),
        }
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
        let compress_flag = dem::IS_COMPRESSED;
        let compressed = (raw_cmd & compress_flag) != 0;
        let cmd = (raw_cmd & !compress_flag) as i32;
        let tick_raw = reader.read_uvarint32()?;
        let tick = tick_raw as i32;
        let body_size = reader.read_uvarint32()?;
        Ok(CmdHeader {
            cmd,
            tick,
            compressed,
            body_size,
        })
    }

    /// Read and decompress a command body into the provided buffer.
    /// The buffer is resized as needed and can be reused across calls.
    fn read_cmd_body(reader: &mut ByteReader, header: &CmdHeader, buf: &mut Vec<u8>) -> Result<()> {
        let raw = reader.read_bytes(header.body_size as usize)?;
        if header.compressed {
            let decompressed_len =
                snap::raw::decompress_len(raw).map_err(|e| Error::Decompress(e.to_string()))?;
            buf.clear();
            buf.resize(decompressed_len, 0);
            snap::raw::Decoder::new()
                .decompress(raw, buf)
                .map_err(|e| Error::Decompress(e.to_string()))?;
        } else {
            buf.clear();
            buf.extend_from_slice(raw);
        }
        Ok(())
    }

    /// Iterate all commands and return metadata about each.
    /// Continues past DEM_Stop to capture DEM_FileInfo.
    pub fn messages(&self) -> Result<Vec<MessageInfo>> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut messages = Vec::new();
        let mut index = 0;

        while reader.remaining() > 0 {
            let offset = reader.position() + HEADER_SIZE;
            let header = match Self::read_cmd_header(&mut reader) {
                Ok(h) => h,
                Err(_) => break,
            };

            messages.push(MessageInfo {
                index,
                cmd: header.cmd,
                cmd_name: command::command_name(header.cmd).to_string(),
                tick: header.tick,
                compressed: header.compressed,
                body_size: header.body_size,
                offset,
            });

            // DEM_Stop has no body, and DEM_FileInfo follows it
            if header.cmd == dem::STOP {
                index += 1;
                continue;
            }

            // DEM_FileInfo comes after DEM_Stop; once we've read it, we're done
            if header.cmd == dem::FILE_INFO {
                reader.skip(header.body_size as usize).ok();
                break;
            }

            if reader.skip(header.body_size as usize).is_err() {
                break;
            }

            index += 1;
        }

        Ok(messages)
    }

    /// Find and decode the CDemoFileHeader message.
    pub fn file_header(&self) -> Result<CDemoFileHeader> {
        if let Some(header) = self.file_header_cache.get() {
            return Ok(header.clone());
        }
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            if header.cmd == dem::FILE_HEADER {
                Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                let decoded = CDemoFileHeader::decode(&body_buf[..])?;
                let _ = self.file_header_cache.set(decoded);
                return Ok(self
                    .file_header_cache
                    .get()
                    .expect("just populated")
                    .clone());
            }

            if header.cmd == dem::STOP {
                break;
            }

            reader.skip(header.body_size as usize)?;
        }

        Err(Error::Parse {
            context: "DEM_FileHeader not found".into(),
        })
    }

    /// Decode CDemoFileInfo using the offset stored in the file header.
    pub fn file_info(&self) -> Result<CDemoFileInfo> {
        if let Some(info) = self.file_info_cache.get() {
            return Ok(info.clone());
        }
        self.verify()?;

        // Bytes 8..12 of the file header contain the absolute offset to DEM_FileInfo.
        let fileinfo_offset = u32::from_le_bytes([
            self.data()[8],
            self.data()[9],
            self.data()[10],
            self.data()[11],
        ]) as usize;

        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        // The offset is relative to the start of the file; adjust for the header we sliced off.
        reader.seek(fileinfo_offset.saturating_sub(HEADER_SIZE))?;

        let header = Self::read_cmd_header(&mut reader)?;
        if header.cmd != dem::FILE_INFO {
            return Err(Error::Parse {
                context: format!(
                    "expected DEM_FileInfo at offset {}, found command {}",
                    fileinfo_offset, header.cmd
                ),
            });
        }

        let mut body_buf = Vec::new();
        Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
        let decoded = CDemoFileInfo::decode(&body_buf[..])?;
        let _ = self.file_info_cache.set(decoded);
        Ok(self.file_info_cache.get().expect("just populated").clone())
    }

    /// Parse game events from the demo.
    ///
    /// Extracts Source 1 legacy game events and user messages from
    /// `DEM_Packet`, `DEM_SignonPacket`, and `DEM_FullPacket` commands.
    /// If `max_tick` is set, stops parsing once the tick exceeds the limit.
    /// Decode the game-event stream, up to `max_tick` if given. Every event
    /// after that tick is skipped. This is the raw decode; prefer [`events`]
    /// (which caches the full stream) unless a partial (`max_tick`) parse is
    /// wanted.
    ///
    /// [`events`]: Parser::events
    pub fn events(&self, max_tick: Option<i32>) -> Result<Vec<GameEvent>> {
        // The full stream is decoded once and cached; a bounded (`max_tick`)
        // request is a partial scan, so it always decodes fresh.
        match max_tick {
            None => Ok(self.events_ref()?.to_vec()),
            Some(_) => self.decode_events(max_tick),
        }
    }

    /// The full, cached event stream — decoded on first call, then reused.
    ///
    /// Internal dataset builders take this slice by reference (no clone); the
    /// public [`events`](Parser::events) hands back an owned copy.
    pub(crate) fn events_ref(&self) -> Result<&[GameEvent]> {
        if let Some(events) = self.events_cache.get() {
            return Ok(events);
        }

        let _guard = self.events_lock.lock().map_err(|_| Error::Parse {
            context: "event cache lock poisoned".into(),
        })?;
        if self.events_cache.get().is_none() {
            let events = self.decode_events(None)?;
            self.events_cache
                .set(events.into())
                .expect("event cache initialized while locked");
        }
        Ok(self.events_cache.get().expect("event cache populated"))
    }

    /// Share the cached full event stream without cloning its event payloads.
    ///
    /// This is useful for bindings and other long-lived consumers that need an
    /// owned handle while preserving the parser's single decoded copy.
    pub fn events_shared(&self) -> Result<Arc<[GameEvent]>> {
        self.events_ref()?;
        Ok(Arc::clone(
            self.events_cache.get().expect("event cache populated"),
        ))
    }

    /// Decode and cache the event stream now, if it isn't already.
    ///
    /// Every dataset pass reads the event stream via `events_ref`, which now
    /// initializes atomically. This remains available as an explicit warm-up
    /// hook for callers that want first-use latency outside a timed operation.
    pub fn prime_events(&self) -> Result<()> {
        self.events_ref()?;
        Ok(())
    }

    fn decode_events(&self, max_tick: Option<i32>) -> Result<Vec<GameEvent>> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut packet_buf = Vec::with_capacity(PACKET_BUF_CAPACITY);
        let mut events = Vec::new();
        let mut descriptors: HashMap<i32, EventDescriptor> = HashMap::new();

        while reader.remaining() > 0 {
            let header = match Self::read_cmd_header(&mut reader) {
                Ok(h) => h,
                Err(_) => break,
            };

            if header.cmd == dem::STOP {
                break;
            }

            if let Some(max) = max_tick
                && header.tick > max
            {
                break;
            }

            match header.cmd {
                dem::PACKET | dem::SIGNON_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_events(
                        &pkt_data,
                        header.tick,
                        &mut descriptors,
                        &mut events,
                        &mut packet_buf,
                    )?;
                }
                dem::FULL_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                    let cmd = CDemoFullPacket::decode(&body_buf[..])?;
                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::process_packet_events(
                            &pkt_data,
                            header.tick,
                            &mut descriptors,
                            &mut events,
                            &mut packet_buf,
                        )?;
                    }
                }
                _ => {
                    reader.skip(header.body_size as usize)?;
                }
            }
        }

        Ok(events)
    }

    /// Server console variables (`net_SetConVar` messages), in stream order.
    ///
    /// Convars mostly arrive in the signon packets; when a name repeats, the
    /// later value is the one in effect.
    pub fn convars(&self) -> Result<Vec<(String, String)>> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut packet_buf = Vec::with_capacity(PACKET_BUF_CAPACITY);
        let mut convars = Vec::new();

        while reader.remaining() > 0 {
            let header = match Self::read_cmd_header(&mut reader) {
                Ok(h) => h,
                Err(_) => break,
            };

            if header.cmd == dem::STOP {
                break;
            }

            match header.cmd {
                dem::PACKET | dem::SIGNON_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::collect_convars(&pkt_data, &mut convars, &mut packet_buf)?;
                }
                dem::FULL_PACKET => {
                    Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                    let cmd = CDemoFullPacket::decode(&body_buf[..])?;
                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::collect_convars(&pkt_data, &mut convars, &mut packet_buf)?;
                    }
                }
                _ => {
                    reader.skip(header.body_size as usize)?;
                }
            }
        }

        Ok(convars)
    }

    /// Scan a packet's inner messages for `net_SetConVar` name/value pairs.
    fn collect_convars(
        pkt_data: &[u8],
        convars: &mut Vec<(String, String)>,
        packet_buf: &mut Vec<u8>,
    ) -> Result<()> {
        let mut br = BitReader::new(pkt_data);

        while br.bits_remaining() > 8 {
            let msg_type = br.read_ubitvar()?;
            let size = br.read_uvarint32()? as usize;

            if msg_type != net::SET_CON_VAR {
                br.skip_bits(size * 8)?;
                continue;
            }

            if size > packet_buf.len() {
                packet_buf.resize(size, 0);
            }
            br.read_bytes(&mut packet_buf[..size])?;

            let msg = CnetMsgSetConVar::decode(&packet_buf[..size])?;
            if let Some(cvars) = msg.convars {
                for cvar in cvars.cvars {
                    convars.push((
                        cvar.name.unwrap_or_default(),
                        cvar.value.unwrap_or_default(),
                    ));
                }
            }
        }

        Ok(())
    }

    /// Process a packet's inner messages for game events.
    fn process_packet_events(
        pkt_data: &[u8],
        tick: i32,
        descriptors: &mut HashMap<i32, EventDescriptor>,
        events: &mut Vec<GameEvent>,
        packet_buf: &mut Vec<u8>,
    ) -> Result<()> {
        let mut br = BitReader::new(pkt_data);

        while br.bits_remaining() > 8 {
            let msg_type = br.read_ubitvar()?;
            let size = br.read_uvarint32()? as usize;

            if !matches!(
                msg_type,
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST
                    | ge::SOURCE1_LEGACY_GAME_EVENT
                    | svc::USER_MESSAGE
            ) {
                br.skip_bits(size * 8)?;
                continue;
            }

            if size > packet_buf.len() {
                packet_buf.resize(size, 0);
            }
            br.read_bytes(&mut packet_buf[..size])?;
            let msg_data = &packet_buf[..size];

            match msg_type {
                ge::SOURCE1_LEGACY_GAME_EVENT_LIST => {
                    let msg = CMsgSource1LegacyGameEventList::decode(msg_data)?;
                    for desc in msg.descriptors {
                        let eventid = desc.eventid.unwrap_or_default();
                        let name = desc.name.unwrap_or_default();
                        let field_names = desc
                            .keys
                            .iter()
                            .map(|k| k.name.clone().unwrap_or_default())
                            .collect();
                        descriptors.insert(eventid, EventDescriptor { name, field_names });
                    }
                }
                ge::SOURCE1_LEGACY_GAME_EVENT => {
                    let msg = CMsgSource1LegacyGameEvent::decode(msg_data)?;
                    let eventid = msg.eventid.unwrap_or_default();
                    let (name, keys) = if let Some(desc) = descriptors.get(&eventid) {
                        let keys: Vec<(String, String)> = desc
                            .field_names
                            .iter()
                            .zip(msg.keys.iter())
                            .map(|(fname, key)| (fname.clone(), format_event_key(key)))
                            .collect();
                        (desc.name.clone(), keys)
                    } else {
                        let name = msg
                            .event_name
                            .unwrap_or_else(|| format!("event_{}", eventid));
                        (name, Vec::new())
                    };
                    events.push(GameEvent {
                        tick,
                        name,
                        msg_type,
                        keys,
                        payload: msg_data.to_vec(),
                    });
                }
                svc::USER_MESSAGE => {
                    let msg = CsvcMsgUserMessage::decode(msg_data)?;
                    let inner_type = msg.msg_type.unwrap_or_default();
                    let name = command::user_message_name(inner_type);
                    let inner_payload = msg.msg_data.unwrap_or_default();
                    events.push(GameEvent {
                        tick,
                        name,
                        msg_type: inner_type as u32,
                        keys: Vec::new(),
                        payload: inner_payload,
                    });
                }
                _ => {
                    // Other packet messages (net messages, etc.) are not game
                    // events. Unlike Deadlock's Citadel messages, CS2 delivers
                    // all user messages wrapped in svc_UserMessage above.
                }
            }
        }

        Ok(())
    }
}
