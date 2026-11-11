# Contribute to Awpy

## Create a branch

Start from the current `main`. Use `<type>/<short-kebab-case-description>`.

| Prefix | Use | Example |
| --- | --- | --- |
| `feat/` | New functionality | `feat/multipart-demos` |
| `fix/` | Bug fixes | `fix/adr-health-rounding` |
| `docs/` | Documentation | `docs/snapshot-examples` |
| `perf/` | Performance changes | `perf/combat-property-filtering` |
| `refactor/` | Code changes that preserve behavior | `refactor/event-dispatch` |
| `test/` | Test changes | `test/trade-boundaries` |
| `chore/` | Dependency, CI, or repository maintenance | `chore/tls-dependencies` |

Use `feat/<version>` for a branch that collects changes for a release, such as
`feat/3.1.3`. Open pull requests against `main` unless the maintainer requests a
different target.

## Set up the tools

Use stable Rust with `rustfmt` and `clippy`, Cargo, cargo-nextest, cargo-deny, and
uv. Install the Rust toolchain with rustup. Prebuilt nextest binaries are also
available. [Rust setup](https://rustup.rs/) · [nextest installation](https://nexte.st/docs/installation/) · [uv installation](https://docs.astral.sh/uv/getting-started/installation/)

```sh
rustup toolchain install stable --component rustfmt --component clippy
rustup default stable
cargo install cargo-nextest --locked
cargo install cargo-deny --locked
uv python install 3.13
```

Use Python 3.11–3.14 to build the local extension. The CI lint job uses 3.13.
CI tests 3.15 with a stable-ABI wheel built with Python 3.14.

## Check Rust code

Run these commands from the repository root.

```sh
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo nextest run --locked --workspace --all-features --exclude awpy-python --failure-output immediate-final
cargo deny --all-features check
```

Use `cargo fmt --all` to apply formatting. Nextest runs the Rust tests.
Pytest checks the native extension through the Python API. Cargo Deny checks
advisories, bans, licenses, and package sources against `deny.toml`.

## Check Python code and build the extension

From the repository root, change to `crates/awpy-python`. Use this directory
for the remaining Python commands.

```sh
cd crates/awpy-python
uv sync --python 3.13 --locked --no-install-project
uv run --no-sync ruff check python tests examples benchmarks
uv run --no-sync ruff format --check python tests examples benchmarks
uv run --no-sync ty check python
uv run --no-sync maturin develop --release --locked
uv run --no-sync pytest -m "not fixtures" -q --durations=10
```

Ruff checks Python code and formatting. Ty checks Python types. Both can run
before the native build. Use `uv run --no-sync ruff format python tests examples benchmarks`
to apply formatting.

Maturin builds and installs the extension from the current checkout. Rebuild it
after Rust changes. Use `uv run --no-sync` after the build to keep the
installed extension. For a focused test run, pass a test file, a test node ID,
or a `-k` expression to pytest.

### Run demo-backed tests

The `fixtures` marker selects tests that need recorded demos. The fixture
manifest lists the downloads and their checksums. The fixture store caches
verified files in `~/.cache/awpy-fixtures` or `AWPY_FIXTURES_DIR`. It can
download several large files. [Awpy fixture repository](https://github.com/pnxenopoulos/awpy-fixtures)

```sh
mkdir -p tests/fixtures
curl -fSL https://raw.githubusercontent.com/pnxenopoulos/awpy-fixtures/main/manifest.json \
  -o tests/fixtures/manifest.json
uv run --no-sync python tests/fixture_store.py
AWPY_RUN_FIXTURES=1 AWPY_TICK_SEGMENTS=2 POLARS_MAX_THREADS=2 \
  uv run --no-sync pytest -m fixtures -q -n 2 --dist=loadfile --durations=10
```

Prepare fixtures before starting test workers so each download completes once.
`AWPY_RUN_FIXTURES=1` permits downloads and makes missing required demos or an
empty manifest fail the tests. Use `--dist=loadfile` to keep each test file
on one worker. If memory is limited, omit `-n 2 --dist=loadfile` for a serial run.
The environment assignments above use POSIX shell syntax. In PowerShell, set
the same values with `$env:NAME = "value"` before running pytest.

Test one behavior per test. Use parameters for input variants and exact table
comparisons where results must match. Share expensive read-only results through
fixtures. Give tests that change cache or parser state fresh instances. Keep
demo files and downloaded manifests out of pull requests.

### Build the documentation

Update the usage guide, docstrings, and type stubs when a public Python API
changes. Build the Sphinx site with warnings treated as errors.

```sh
uv sync --python 3.13 --locked --group docs --no-install-project
uv run --no-sync maturin develop --release --locked
uv run --no-sync sphinx-build -W -b html docs docs/_build/html
```

## Update dependencies and lockfiles

- **Python.** Edit `crates/awpy-python/pyproject.toml` with `uv add` or
  `uv remove` from `crates/awpy-python`. Put development tools in `dev`,
  documentation tools in `docs`, and optional runtime dependencies in the
  applicable extra. For a targeted lockfile update, use
  `uv lock --upgrade-package typer`, for example. Run `uv lock --check` and
  include any resulting `uv.lock` change. [uv lockfile guide](https://docs.astral.sh/uv/concepts/projects/sync/)
- **Rust.** Put shared constraints in `[workspace.dependencies]` and
  crate-specific dependencies in that crate's `Cargo.toml`. Use
  `cargo update -p pbdems2`, for example, to update one package within its
  constraint. Use `cargo tree --locked -i pbdems2` to see which crates depend on it.
  Include the resulting `Cargo.lock` change. The protobuf generator has a separate
  lockfile under `scripts/build-protos`.
- Review lockfile diffs for unrelated upgrades. Keep Rust dependencies compatible
  with the declared Rust version and the Python binding dependencies compatible
  with the supported Python versions. Run the relevant checks after a change.
- Prefer a compatible dependency update for a security advisory. If a Cargo Deny
  exception is necessary, record the advisory, why it does not apply to Awpy,
  and when to remove the exception.

## Open a pull request

- Describe the change, the expected behavior, and the checks you ran. For a
  replay bug, include the demo source and the relevant round or tick when available.
- Add a regression test for a behavior fix. For parser performance changes,
  compare the same inputs and outputs before and after. [Benchmark guide](crates/awpy/benches/README.md)
- Add a short entry for user-facing changes under the applicable release heading
  in the [changelog](crates/awpy-python/docs/changelog.md). For protobuf or release
  work, follow the [protobuf instructions](crates/awpy-proto/README.md) or the
  [release instructions](README.md#releases).
