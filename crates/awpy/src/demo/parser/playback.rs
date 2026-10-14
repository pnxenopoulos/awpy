use pbdems2::{DemoParser, PreparedPlayback};

use crate::entity::{ClassInfo, SerializerContainer};
use crate::error::{Error, Result};

use super::{Context, Cs2Adapter, DEFAULT_TICK_INTERVAL, GameEvent, HEADER_SIZE, Parser};

impl Parser {
    fn demo_parser(&self) -> Result<DemoParser<'_>> {
        DemoParser::new(self.data()).map_err(Error::from)
    }

    fn prepared(&self) -> Result<&PreparedPlayback<Cs2Adapter>> {
        if let Some(prepared) = self.prepared_cache.get() {
            return Ok(prepared);
        }

        let _guard = self.prepared_lock.lock().map_err(|_| Error::Parse {
            context: "prepared-playback cache lock poisoned".into(),
        })?;
        if self.prepared_cache.get().is_none() {
            let prepared = self
                .demo_parser()?
                .prepare(Cs2Adapter::default(), DEFAULT_TICK_INTERVAL)?;
            self.prepared_cache.set(prepared).unwrap_or_else(|_| {
                unreachable!("prepared-playback cache initialized while locked")
            });
        }
        Ok(self
            .prepared_cache
            .get()
            .expect("prepared-playback cache populated"))
    }

    /// Parse send tables from the signon stream.
    pub fn parse_send_tables(&self) -> Result<SerializerContainer> {
        Ok(self.prepared()?.initial_state().serializers().clone())
    }

    /// Parse network class information from the signon stream.
    pub fn parse_class_info(&self) -> Result<ClassInfo> {
        Ok(self.prepared()?.initial_state().class_info().clone())
    }

    /// Parse all initialization data through `DEM_SyncTick`.
    pub fn parse_init(&self) -> Result<Context> {
        Ok(self.prepared()?.initial_state().clone())
    }

    /// Parse the demo to a specific tick, restoring the nearest full packet.
    pub fn parse_to_tick(&self, target_tick: i32) -> Result<Context> {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.parse_to_tick(target_tick)
    }

    /// Parse the entire demo, calling a callback once per completed tick.
    pub fn run_to_end<F>(&self, on_tick: F) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.run_to_end(on_tick)?;
        Ok(())
    }

    /// Parse the entire demo while materializing only selected entity classes.
    pub fn run_to_end_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?
            .session(parser)?
            .run_to_end_filtered(class_filter, on_tick)?;
        Ok(())
    }

    /// Parse entities and game events in one filtered pass.
    pub fn run_to_end_with_events_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let parser = self.demo_parser()?;
        let mut session = self.prepared()?.session(parser)?;
        session.adapter_mut().enable_events();
        session.run_to_end_filtered_with_adapter(class_filter, |state, adapter| {
            on_tick(state, adapter.tick_events());
            adapter.clear_tick_events();
        })?;
        Ok(())
    }

    /// Parse entities and only selected legacy events in one filtered pass.
    ///
    /// Raw event payloads are omitted: callers of this path consume the decoded
    /// legacy key/value pairs and avoid allocating protobuf bytes they will not
    /// use.
    pub(crate) fn run_to_end_with_legacy_events_filtered<F>(
        &self,
        class_filter: &std::collections::HashSet<&str>,
        event_names: &std::collections::HashSet<&str>,
        mut on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context, &[GameEvent]),
    {
        let parser = self.demo_parser()?;
        let mut session = self.prepared()?.session(parser)?;
        session
            .adapter_mut()
            .enable_legacy_events(event_names.iter().copied(), false);
        session.run_to_end_filtered_with_adapter(class_filter, |state, adapter| {
            on_tick(state, adapter.tick_events());
            adapter.clear_tick_events();
        })?;
        Ok(())
    }

    /// Byte offsets relative to the post-header stream and ticks of full packets.
    pub fn full_packet_offsets(&self) -> Result<Vec<(usize, i32)>> {
        Ok(self
            .prepared()?
            .index()
            .full_packets()
            .iter()
            .map(|position| (position.offset() - HEADER_SIZE, position.tick()))
            .collect())
    }

    /// Every distinct post-signon tick in ascending stream order.
    pub fn distinct_ticks(&self) -> Result<Vec<i32>> {
        Ok(self.prepared()?.index().distinct_ticks().to_vec())
    }

    /// Decode one full-packet-bounded segment for parallel consumers.
    pub fn decode_segment<F>(
        &self,
        start: Option<usize>,
        end_tick: i32,
        class_filter: &std::collections::HashSet<&str>,
        on_tick: F,
    ) -> Result<()>
    where
        F: FnMut(&Context),
    {
        let parser = self.demo_parser()?;
        self.prepared()?.session(parser)?.decode_segment(
            start.map(|offset| offset + HEADER_SIZE),
            end_tick,
            class_filter,
            on_tick,
        )?;
        Ok(())
    }
}
