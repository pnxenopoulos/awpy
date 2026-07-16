# awpy-proto

Generated [prost](https://docs.rs/prost) types for the **Counter-Strike 2**
protobuf definitions used when parsing demo files.

The `.proto` sources under `proto/` are synced from
[GameTracking-CS2](https://github.com/SteamDatabase/GameTracking-CS2); the
allowlist in `proto/allowlist.txt` records which files are compiled (it must be
closed under `import`). The checked-in `src/proto.rs` is regenerated with:

```sh
cargo run --manifest-path scripts/build-protos/Cargo.toml
```

from the workspace root. Do not edit `src/proto.rs` by hand.

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
