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

## Check for updates

Run this command from the workspace root:

```sh
./scripts/sync-protos.sh --check
```

The check compares the allowlisted files with upstream. It ignores line-ending
differences and does not change local files or versions. It exits with a nonzero
status if files differ, a local file is missing, or the check cannot finish.
Set `CS2_REF` to a branch, tag, or commit to check a specific revision.

CI runs the same check as **Protobuf Freshness (advisory)**. It writes a job
summary and a warning if the check fails. It does not block CI Check or releases.

To update the files and package version, then generate the Rust types, run:

```sh
./scripts/sync-protos.sh
cargo run --manifest-path scripts/build-protos/Cargo.toml
```

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
