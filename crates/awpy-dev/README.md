# awpy-dev

Developer CLI (`awpy-dev`) for inspecting **Counter-Strike 2** demo files and
parser internals. The user-facing `awpy` command ships with the
[Python package](../awpy-python) (`pip install awpy`); this binary is the
Rust-side harness for hacking on the parser itself — no Python required.

```sh
cargo install --path crates/awpy-dev   # installs `awpy-dev`
```

## Commands

Parser internals (not exposed in the Python API):

| Command         | Description                                              |
| --------------- | -------------------------------------------------------- |
| `messages`      | List the demo command stream.                            |
| `classes`       | List entity classes (network name ↔ class id).           |
| `send-tables`   | Show flattened serializers (entity field definitions).   |
| `string-tables` | Show string tables and their entries.                    |
| `entities`      | Snapshot entities at a tick (`--fields` to decode them). |

Plus Rust-side equivalents of the Python CLI's inspection commands, for
validating the core without building a wheel: `verify`, `info`, `events`,
`rounds`, `kills`, `damage`, `bomb`, `shots`, `grenades`, `fires`, `smokes`,
`blinds`, `item-events`, `stats`.

Every command accepts `--json` for machine-readable output. Examples:

```sh
awpy-dev info match.dem
awpy-dev events match.dem --summary --max-tick 30000
awpy-dev entities match.dem --tick 100000 --class CCSPlayerPawn --fields
```

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
