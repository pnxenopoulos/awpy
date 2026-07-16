use std::path::Path;

use memmap2::Mmap;
use prost::Message;

use crate::entity::{
    ClassInfo, EntityContainer, FieldDecodeContext, SerializerContainer, StringTableContainer,
};
use crate::error::{Error, Result};
use crate::io::{BitReader, ByteReader};

use std::collections::HashMap;
use std::sync::OnceLock;

use super::command::{self, CmdHeader, dem, ge, net, svc};

use awpy_proto::proto::{
    CDemoClassInfo, CDemoFileHeader, CDemoFileInfo, CDemoFullPacket, CDemoPacket, CDemoSendTables,
    CMsgSource1LegacyGameEvent, CMsgSource1LegacyGameEventList, CnetMsgSetConVar,
    CsvcMsgCreateStringTable, CsvcMsgPacketEntities, CsvcMsgServerInfo, CsvcMsgUpdateStringTable,
    CsvcMsgUserMessage,
};

/// Magic bytes at the start of every Source 2 demo file.
const MAGIC: &[u8; 8] = b"PBDEMS2\0";
/// File header: 8 bytes magic + 4 bytes fileinfo_offset + 4 bytes spawngroups_offset.
const HEADER_SIZE: usize = 16;

/// Default tick rate (1/64 s — CS2's standard server tick). Used to compute
/// `full_packet_interval` before `CSVCMsg_ServerInfo.tick_interval` is seen.
const DEFAULT_TICK_INTERVAL: f32 = 1.0 / 64.0;
/// Default number of ticks between full-packet snapshots (at 64 Hz).
///
/// Only a seek hint for [`Parser::parse_to_tick`]; correctness does not depend
/// on the exact value, so this is scaled by the real tick interval once known.
const DEFAULT_FULL_PACKET_INTERVAL: i32 = 1800;

/// Scratch buffer size for decompressed command bodies and packet payloads.
const BUF_SIZE: usize = 2 * 1024 * 1024;

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
pub struct Context {
    /// Field definitions for every entity class.
    pub serializers: SerializerContainer,
    /// Maps numeric class IDs to network names.
    pub class_info: ClassInfo,
    /// Key-value tables (models, sounds, instance baselines, etc.).
    pub string_tables: StringTableContainer,
    /// Currently active entities keyed by entity index.
    pub entities: EntityContainer,
    /// Seconds per tick (from `CSVCMsg_ServerInfo`).
    pub tick_interval: f32,
    /// Ticks between full-packet snapshots (derived from tick_interval).
    pub full_packet_interval: i32,
    /// Most recent tick processed.
    pub tick: i32,
}

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
    events_cache: OnceLock<Vec<GameEvent>>,
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
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            if header.cmd == dem::FILE_HEADER {
                Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                return CDemoFileHeader::decode(&body_buf[..]).map_err(Error::from);
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
        CDemoFileInfo::decode(&body_buf[..]).map_err(Error::from)
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
        if self.events_cache.get().is_none() {
            let events = self.decode_events(None)?;
            // Another thread may have won the race; either stored vec is fine.
            let _ = self.events_cache.set(events);
        }
        Ok(self.events_cache.get().expect("just populated"))
    }

    /// Decode and cache the event stream now, if it isn't already.
    ///
    /// Every dataset pass reads the event stream via `events_ref`,
    /// which decodes it lazily on first use. When several passes run **concurrently**
    /// on a fresh parser they would otherwise each decode it redundantly (the cache
    /// is populated with a benign check-then-set race). Call this once serially
    /// beforehand so the parallel passes all reuse the single cached copy.
    pub fn prime_events(&self) -> Result<()> {
        self.events_ref()?;
        Ok(())
    }

    fn decode_events(&self, max_tick: Option<i32>) -> Result<Vec<GameEvent>> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut packet_buf = vec![0u8; BUF_SIZE];
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
        let mut packet_buf = vec![0u8; BUF_SIZE];
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

            if size > packet_buf.len() {
                packet_buf.resize(size, 0);
            }
            br.read_bytes(&mut packet_buf[..size])?;

            if msg_type == net::SET_CON_VAR {
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

    /// Parse send tables from DEM_SendTables command.
    pub fn parse_send_tables(&self) -> Result<SerializerContainer> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            if header.cmd == dem::SEND_TABLES {
                Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                let cmd = CDemoSendTables::decode(&body_buf[..])?;
                return SerializerContainer::parse(cmd);
            }

            if header.cmd == dem::STOP || header.cmd == dem::SYNC_TICK {
                break;
            }

            reader.skip(header.body_size as usize)?;
        }

        Err(Error::Parse {
            context: "DEM_SendTables not found".into(),
        })
    }

    /// Parse class info from DEM_ClassInfo command.
    pub fn parse_class_info(&self) -> Result<ClassInfo> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);
        let mut body_buf = Vec::with_capacity(BUF_SIZE);

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            if header.cmd == dem::CLASS_INFO {
                Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                let cmd = CDemoClassInfo::decode(&body_buf[..])?;
                return Ok(ClassInfo::parse(cmd));
            }

            if header.cmd == dem::STOP || header.cmd == dem::SYNC_TICK {
                break;
            }

            reader.skip(header.body_size as usize)?;
        }

        Err(Error::Parse {
            context: "DEM_ClassInfo not found".into(),
        })
    }

    /// Parse all initialization data up to DEM_SyncTick and return a Context.
    pub fn parse_init(&self) -> Result<Context> {
        self.verify()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);

        let mut packet_buf = vec![0u8; BUF_SIZE];
        let mut body_buf = Vec::with_capacity(BUF_SIZE);

        let mut serializers: Option<SerializerContainer> = None;
        let mut class_info: Option<ClassInfo> = None;
        let mut string_tables = StringTableContainer::new();
        let mut tick_interval: f32 = 0.0;
        let mut full_packet_interval: i32 = DEFAULT_FULL_PACKET_INTERVAL;

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            if header.cmd == dem::SYNC_TICK {
                reader.skip(header.body_size as usize)?;
                break;
            }

            if header.cmd == dem::STOP {
                break;
            }

            Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;

            match header.cmd {
                dem::SEND_TABLES => {
                    let cmd = CDemoSendTables::decode(&body_buf[..])?;
                    serializers = Some(SerializerContainer::parse(cmd)?);
                }
                dem::CLASS_INFO => {
                    let cmd = CDemoClassInfo::decode(&body_buf[..])?;
                    class_info = Some(ClassInfo::parse(cmd));
                }
                dem::PACKET | dem::SIGNON_PACKET => {
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_for_init(
                        &pkt_data,
                        &mut string_tables,
                        &mut tick_interval,
                        &mut full_packet_interval,
                        &mut packet_buf,
                    )?;
                }
                _ => {}
            }
        }

        let serializers = serializers.ok_or_else(|| Error::Parse {
            context: "DEM_SendTables not found during init".into(),
        })?;
        let class_info = class_info.ok_or_else(|| Error::Parse {
            context: "DEM_ClassInfo not found during init".into(),
        })?;

        // Update instance baselines
        string_tables.update_instance_baselines(&class_info);

        Ok(Context {
            serializers,
            class_info,
            string_tables,
            entities: EntityContainer::new(),
            tick_interval,
            full_packet_interval,
            tick: -1,
        })
    }

    /// Process a packet's inner messages during initialization (string tables, server info).
    fn process_packet_for_init(
        pkt_data: &[u8],
        string_tables: &mut StringTableContainer,
        tick_interval: &mut f32,
        full_packet_interval: &mut i32,
        packet_buf: &mut Vec<u8>,
    ) -> Result<()> {
        let mut br = BitReader::new(pkt_data);

        while br.bits_remaining() > 8 {
            let msg_type = br.read_ubitvar()?;
            let size = br.read_uvarint32()? as usize;

            // Read the message body
            if size > packet_buf.len() {
                packet_buf.resize(size, 0);
            }
            br.read_bytes(&mut packet_buf[..size])?;
            let msg_data = &packet_buf[..size];

            match msg_type {
                svc::CREATE_STRING_TABLE => {
                    let msg = CsvcMsgCreateStringTable::decode(msg_data)?;
                    string_tables.handle_create(msg)?;
                }
                svc::UPDATE_STRING_TABLE => {
                    let msg = CsvcMsgUpdateStringTable::decode(msg_data)?;
                    string_tables.handle_update(msg)?;
                }
                svc::SERVER_INFO => {
                    let msg = CsvcMsgServerInfo::decode(msg_data)?;
                    if let Some(ti) = msg.tick_interval {
                        *tick_interval = ti;
                        let ratio = DEFAULT_TICK_INTERVAL / ti;
                        *full_packet_interval = DEFAULT_FULL_PACKET_INTERVAL * ratio as i32;
                    }
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Parse the demo to a specific tick, returning the full game state.
    ///
    /// Skips forward to the last `DEM_FullPacket` snapshot at or before
    /// `target_tick`, applies that snapshot, then replays individual packets
    /// until `target_tick` is reached. The snapshot is located exactly with a
    /// cheap header-only pre-scan — full-packet spacing varies by demo, so it
    /// cannot be predicted from the tick interval.
    pub fn parse_to_tick(&self, target_tick: i32) -> Result<Context> {
        let mut ctx = self.parse_init()?;
        let data = &self.data()[HEADER_SIZE..];

        // Header-only pre-scan: byte offset of the last full packet <= target.
        let mut last_full_packet: Option<usize> = None;
        {
            let mut scan = ByteReader::new(data);
            while scan.remaining() > 0 {
                let pos = scan.position();
                let header = match Self::read_cmd_header(&mut scan) {
                    Ok(h) => h,
                    Err(_) => break,
                };
                if header.cmd == dem::STOP || header.tick > target_tick {
                    break;
                }
                if header.cmd == dem::FULL_PACKET {
                    last_full_packet = Some(pos);
                }
                scan.skip(header.body_size as usize)?;
            }
        }

        let mut reader = ByteReader::new(data);
        let mut packet_buf = vec![0u8; BUF_SIZE];
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut fp_buf = Vec::with_capacity(256);
        let mut field_decode_ctx = FieldDecodeContext::new(ctx.tick_interval);

        // Skip past init (up to and including SyncTick)
        let mut past_sync = false;
        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;
            if header.cmd == dem::SYNC_TICK {
                reader.skip(header.body_size as usize)?;
                past_sync = true;
                break;
            }
            if header.cmd == dem::STOP {
                return Ok(ctx);
            }
            reader.skip(header.body_size as usize)?;
        }

        if !past_sync {
            return Ok(ctx);
        }

        // Replay deltas only once the snapshot they build on has been applied.
        // With no full packet before the target, replay from the signon
        // baseline instead.
        let mut did_handle_last_full_packet = last_full_packet.is_none();

        while reader.remaining() > 0 {
            let cmd_offset = reader.position();
            let header = Self::read_cmd_header(&mut reader)?;

            if header.tick > target_tick && header.cmd != dem::STOP {
                break;
            }

            ctx.tick = header.tick;

            if header.cmd == dem::STOP {
                break;
            }

            if header.cmd == dem::FULL_PACKET {
                Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;
                let cmd = CDemoFullPacket::decode(&body_buf[..])?;

                // Handle string tables from full packet
                if let Some(st) = cmd.string_table {
                    ctx.string_tables.do_full_update(st);
                    ctx.string_tables.update_instance_baselines(&ctx.class_info);
                }

                // Apply entity state only from the snapshot we replay from.
                if Some(cmd_offset) == last_full_packet {
                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::process_packet_entities(
                            &pkt_data,
                            &mut ctx,
                            &mut field_decode_ctx,
                            &mut packet_buf,
                            &mut fp_buf,
                        )?;
                    }
                    did_handle_last_full_packet = true;
                }

                continue;
            }

            if !did_handle_last_full_packet {
                reader.skip(header.body_size as usize)?;
                continue;
            }

            Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;

            match header.cmd {
                dem::PACKET | dem::SIGNON_PACKET => {
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_entities(
                        &pkt_data,
                        &mut ctx,
                        &mut field_decode_ctx,
                        &mut packet_buf,
                        &mut fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(ctx)
    }

    /// Parse the entire demo, calling a callback at each tick with the current context.
    /// This is more efficient than calling parse_to_tick repeatedly.
    pub fn run_to_end<F>(&self, mut on_tick: F) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let mut ctx = self.parse_init()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);

        let mut packet_buf = vec![0u8; BUF_SIZE];
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut fp_buf = Vec::with_capacity(256);
        let mut field_decode_ctx = FieldDecodeContext::new(ctx.tick_interval);

        // Skip past init (up to and including SyncTick)
        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;
            if header.cmd == dem::SYNC_TICK {
                reader.skip(header.body_size as usize)?;
                break;
            }
            if header.cmd == dem::STOP {
                return Ok(());
            }
            reader.skip(header.body_size as usize)?;
        }

        let mut last_tick: i32 = -1;

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            // Call callback when tick changes
            if header.tick != last_tick && last_tick >= 0 {
                on_tick(&ctx);
                ctx.string_tables.clear_dirty();
            }
            last_tick = header.tick;
            ctx.tick = header.tick;

            if header.cmd == dem::STOP {
                // Final callback
                if last_tick >= 0 {
                    on_tick(&ctx);
                }
                break;
            }

            Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;

            match header.cmd {
                dem::FULL_PACKET => {
                    let cmd = CDemoFullPacket::decode(&body_buf[..])?;

                    if let Some(st) = cmd.string_table {
                        ctx.string_tables.do_full_update(st);
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }

                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::process_packet_entities(
                            &pkt_data,
                            &mut ctx,
                            &mut field_decode_ctx,
                            &mut packet_buf,
                            &mut fp_buf,
                        )?;
                    }
                }
                dem::PACKET | dem::SIGNON_PACKET => {
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_entities(
                        &pkt_data,
                        &mut ctx,
                        &mut field_decode_ctx,
                        &mut packet_buf,
                        &mut fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Parse the entire demo with entity class filtering.
    /// Only entities with classes in the filter are fully tracked.
    /// This is much faster when you only need specific entity types.
    pub fn run_to_end_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let mut ctx = self.parse_init()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = ByteReader::new(data);

        let mut packet_buf = vec![0u8; BUF_SIZE];
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut fp_buf = Vec::with_capacity(256);
        let mut field_decode_ctx = FieldDecodeContext::new(ctx.tick_interval);

        // Skip past init (up to and including SyncTick)
        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;
            if header.cmd == dem::SYNC_TICK {
                reader.skip(header.body_size as usize)?;
                break;
            }
            if header.cmd == dem::STOP {
                return Ok(());
            }
            reader.skip(header.body_size as usize)?;
        }

        let mut last_tick: i32 = -1;

        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            // Call callback when tick changes
            if header.tick != last_tick && last_tick >= 0 {
                on_tick(&ctx);
                ctx.string_tables.clear_dirty();
            }
            last_tick = header.tick;
            ctx.tick = header.tick;

            if header.cmd == dem::STOP {
                // Final callback
                if last_tick >= 0 {
                    on_tick(&ctx);
                }
                break;
            }

            Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;

            match header.cmd {
                dem::FULL_PACKET => {
                    let cmd = CDemoFullPacket::decode(&body_buf[..])?;

                    if let Some(st) = cmd.string_table {
                        ctx.string_tables.do_full_update(st);
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }

                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::process_packet_entities_filtered(
                            &pkt_data,
                            &mut ctx,
                            &mut field_decode_ctx,
                            &mut packet_buf,
                            class_filter,
                            &mut fp_buf,
                        )?;
                    }
                }
                dem::PACKET | dem::SIGNON_PACKET => {
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_entities_filtered(
                        &pkt_data,
                        &mut ctx,
                        &mut field_decode_ctx,
                        &mut packet_buf,
                        class_filter,
                        &mut fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Byte offset (relative to the post-`HEADER_SIZE` data) and tick of every
    /// `DEM_FullPacket` keyframe, via a cheap header-only pre-scan.
    ///
    /// Full packets are periodic snapshots the parallel tick decoder cold-restarts
    /// from — each is a segment boundary. Returned in ascending order.
    pub fn full_packet_offsets(&self) -> Result<Vec<(usize, i32)>> {
        let data = &self.data()[HEADER_SIZE..];
        let mut scan = ByteReader::new(data);
        let mut offsets = Vec::new();
        while scan.remaining() > 0 {
            let pos = scan.position();
            let header = match Self::read_cmd_header(&mut scan) {
                Ok(h) => h,
                Err(_) => break,
            };
            if header.cmd == dem::STOP {
                break;
            }
            if header.cmd == dem::FULL_PACKET {
                offsets.push((pos, header.tick));
            }
            scan.skip(header.body_size as usize)?;
        }
        Ok(offsets)
    }

    /// Every distinct tick in the demo (ascending), from a header-only pre-scan
    /// starting after `DEM_SyncTick` — i.e. the ticks a decode actually emits.
    ///
    /// Lets a sampled pass (stride snapshots) compute which ticks to sample once,
    /// independently of how the demo is later split into parallel segments.
    pub fn distinct_ticks(&self) -> Result<Vec<i32>> {
        let data = &self.data()[HEADER_SIZE..];
        let mut scan = ByteReader::new(data);

        // Skip init up to and including SyncTick, matching the decode's start.
        let mut past_sync = false;
        while scan.remaining() > 0 {
            let header = Self::read_cmd_header(&mut scan)?;
            if header.cmd == dem::STOP {
                return Ok(Vec::new());
            }
            scan.skip(header.body_size as usize)?;
            if header.cmd == dem::SYNC_TICK {
                past_sync = true;
                break;
            }
        }
        if !past_sync {
            return Ok(Vec::new());
        }

        let mut ticks = Vec::new();
        let mut last = i32::MIN;
        while scan.remaining() > 0 {
            let header = match Self::read_cmd_header(&mut scan) {
                Ok(h) => h,
                Err(_) => break,
            };
            if header.cmd == dem::STOP {
                break;
            }
            if header.tick != last && header.tick >= 0 {
                ticks.push(header.tick);
                last = header.tick;
            }
            scan.skip(header.body_size as usize)?;
        }
        Ok(ticks)
    }

    /// Decode one contiguous segment of the demo, for the parallel tick path.
    ///
    /// `start` selects where decoding begins: `None` starts from the signon
    /// baseline (the first segment); `Some(offset)` cold-restarts at the
    /// `DEM_FullPacket` at that byte offset (from `full_packet_offsets`),
    /// applying its snapshot. `on_tick` fires once per completed tick whose value
    /// is `< end_tick` (pass [`i32::MAX`] for the final segment).
    ///
    /// **Exact for player pawn/controller data only.** Those entities are fully
    /// re-keyframed at every full packet, so a cold restart reproduces their exact
    /// state — which is what lets the per-segment decodes be stitched back into the
    /// same result as one serial pass. "Sticky" non-player entities (weapons, held
    /// grenades, spray decals, dropped C4) are *not* re-keyframed by full packets
    /// and would read stale from a cold restart, so this must not be used to build
    /// datasets that read them.
    pub fn decode_segment<F>(
        &self,
        start: Option<usize>,
        end_tick: i32,
        class_filter: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let mut ctx = self.parse_init()?;
        let data = &self.data()[HEADER_SIZE..];
        let mut reader = match start {
            Some(off) => ByteReader::new(&data[off..]),
            None => {
                // Skip past init (up to and including SyncTick).
                let mut r = ByteReader::new(data);
                loop {
                    if r.remaining() == 0 {
                        return Ok(());
                    }
                    let header = Self::read_cmd_header(&mut r)?;
                    if header.cmd == dem::SYNC_TICK {
                        r.skip(header.body_size as usize)?;
                        break;
                    }
                    if header.cmd == dem::STOP {
                        return Ok(());
                    }
                    r.skip(header.body_size as usize)?;
                }
                r
            }
        };

        let mut packet_buf = vec![0u8; BUF_SIZE];
        let mut body_buf = Vec::with_capacity(BUF_SIZE);
        let mut fp_buf = Vec::with_capacity(256);
        let mut field_decode_ctx = FieldDecodeContext::new(ctx.tick_interval);

        let mut last_tick: i32 = -1;
        while reader.remaining() > 0 {
            let header = Self::read_cmd_header(&mut reader)?;

            // Reaching the next segment's first tick ends this one: emit the last
            // completed tick, then stop.
            if header.cmd != dem::STOP && header.tick >= end_tick {
                if last_tick >= 0 {
                    on_tick(&ctx);
                }
                return Ok(());
            }

            if header.tick != last_tick && last_tick >= 0 {
                on_tick(&ctx);
                ctx.string_tables.clear_dirty();
            }
            last_tick = header.tick;
            ctx.tick = header.tick;

            if header.cmd == dem::STOP {
                if last_tick >= 0 {
                    on_tick(&ctx);
                }
                break;
            }

            Self::read_cmd_body(&mut reader, &header, &mut body_buf)?;

            match header.cmd {
                dem::FULL_PACKET => {
                    let cmd = CDemoFullPacket::decode(&body_buf[..])?;
                    if let Some(st) = cmd.string_table {
                        ctx.string_tables.do_full_update(st);
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }
                    if let Some(packet) = cmd.packet {
                        let pkt_data = packet.data.unwrap_or_default();
                        Self::process_packet_entities_filtered(
                            &pkt_data,
                            &mut ctx,
                            &mut field_decode_ctx,
                            &mut packet_buf,
                            class_filter,
                            &mut fp_buf,
                        )?;
                    }
                }
                dem::PACKET | dem::SIGNON_PACKET => {
                    let cmd = CDemoPacket::decode(&body_buf[..])?;
                    let pkt_data = cmd.data.unwrap_or_default();
                    Self::process_packet_entities_filtered(
                        &pkt_data,
                        &mut ctx,
                        &mut field_decode_ctx,
                        &mut packet_buf,
                        class_filter,
                        &mut fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Process a packet's inner messages for entity updates.
    fn process_packet_entities(
        pkt_data: &[u8],
        ctx: &mut Context,
        field_decode_ctx: &mut FieldDecodeContext,
        packet_buf: &mut Vec<u8>,
        fp_buf: &mut Vec<crate::entity::field_path::FieldPath>,
    ) -> Result<()> {
        let mut br = BitReader::new(pkt_data);

        while br.bits_remaining() > 8 {
            let msg_type = br.read_ubitvar()?;
            let size = br.read_uvarint32()? as usize;

            // Only these four message types are consumed below; advance past
            // everything else without copying its bytes out of the bitstream.
            if !matches!(
                msg_type,
                svc::CREATE_STRING_TABLE
                    | svc::UPDATE_STRING_TABLE
                    | svc::SERVER_INFO
                    | svc::PACKET_ENTITIES
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
                svc::CREATE_STRING_TABLE => {
                    let msg = CsvcMsgCreateStringTable::decode(msg_data)?;
                    if ctx.string_tables.handle_create(msg)? {
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }
                }
                svc::UPDATE_STRING_TABLE => {
                    let msg = CsvcMsgUpdateStringTable::decode(msg_data)?;
                    if ctx.string_tables.handle_update(msg)? {
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }
                }
                svc::SERVER_INFO => {
                    let msg = CsvcMsgServerInfo::decode(msg_data)?;
                    if let Some(ti) = msg.tick_interval {
                        ctx.tick_interval = ti;
                        field_decode_ctx.tick_interval = ti;
                        let ratio = DEFAULT_TICK_INTERVAL / ti;
                        ctx.full_packet_interval = DEFAULT_FULL_PACKET_INTERVAL * ratio as i32;
                    }
                }
                svc::PACKET_ENTITIES => {
                    let msg = CsvcMsgPacketEntities::decode(msg_data)?;
                    ctx.entities.handle_packet_entities(
                        msg,
                        &ctx.class_info,
                        &ctx.serializers,
                        &ctx.string_tables,
                        field_decode_ctx,
                        fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(())
    }

    /// Process a packet's inner messages with entity class filtering.
    fn process_packet_entities_filtered(
        pkt_data: &[u8],
        ctx: &mut Context,
        field_decode_ctx: &mut FieldDecodeContext,
        packet_buf: &mut Vec<u8>,
        class_filter: &std::collections::HashSet<&str>,
        fp_buf: &mut Vec<crate::entity::field_path::FieldPath>,
    ) -> Result<()> {
        let mut br = BitReader::new(pkt_data);

        while br.bits_remaining() > 8 {
            let msg_type = br.read_ubitvar()?;
            let size = br.read_uvarint32()? as usize;

            // Only these four message types are consumed below; advance past
            // everything else without copying its bytes out of the bitstream.
            if !matches!(
                msg_type,
                svc::CREATE_STRING_TABLE
                    | svc::UPDATE_STRING_TABLE
                    | svc::SERVER_INFO
                    | svc::PACKET_ENTITIES
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
                svc::CREATE_STRING_TABLE => {
                    let msg = CsvcMsgCreateStringTable::decode(msg_data)?;
                    if ctx.string_tables.handle_create(msg)? {
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }
                }
                svc::UPDATE_STRING_TABLE => {
                    let msg = CsvcMsgUpdateStringTable::decode(msg_data)?;
                    if ctx.string_tables.handle_update(msg)? {
                        ctx.string_tables.update_instance_baselines(&ctx.class_info);
                    }
                }
                svc::SERVER_INFO => {
                    let msg = CsvcMsgServerInfo::decode(msg_data)?;
                    if let Some(ti) = msg.tick_interval {
                        ctx.tick_interval = ti;
                        field_decode_ctx.tick_interval = ti;
                        let ratio = DEFAULT_TICK_INTERVAL / ti;
                        ctx.full_packet_interval = DEFAULT_FULL_PACKET_INTERVAL * ratio as i32;
                    }
                }
                svc::PACKET_ENTITIES => {
                    let msg = CsvcMsgPacketEntities::decode(msg_data)?;
                    ctx.entities.handle_packet_entities_filtered(
                        msg,
                        &ctx.class_info,
                        &ctx.serializers,
                        &ctx.string_tables,
                        field_decode_ctx,
                        class_filter,
                        fp_buf,
                    )?;
                }
                _ => {}
            }
        }

        Ok(())
    }
}
