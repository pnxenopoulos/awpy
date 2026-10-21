# awpy-dev

```sh
cargo install --path crates/awpy-dev   # installs `awpy-dev`
```

Use `awpy-dev` to inspect CS2 demos and parser internals without Python.
For the user CLI, install the [Python package](../awpy-python).



<a id="commands"></a>

## Inspect CS2 demos with awpy-dev

Parser internals (not exposed in the Python API):

| Command         | Description                                              |
| --------------- | -------------------------------------------------------- |
| `messages`      | List the demo command stream.                            |
| `classes`       | List entity classes (network name ↔ class id).           |
| `send-tables`   | Show flattened serializers (entity field definitions).   |
| `string-tables` | Show string tables and their entries.                    |
| `entities`      | Snapshot entities at a tick (`--fields` to decode them). |

The CLI also provides: `verify`, `info`, `events`,
`rounds`, `kills`, `damage`, `bomb`, `shots`, `grenades`, `fires`, `smokes`,
`blinds`, `item-events`, `stats`.

Most commands support `--json`. The `entities`, `send-tables`, and
`string-tables` commands print text even when this flag is set.

Examples:

```sh
awpy-dev info match.dem
awpy-dev events match.dem --summary --max-tick 30000
awpy-dev entities match.dem --tick 100000 --class CCSPlayerPawn --fields
```

Part of the [Awpy](https://github.com/pnxenopoulos/awpy) workspace.

## License

MIT
