#!/usr/bin/env bash
set -euo pipefail

# Sync CS2 protos + version info into ../crates/awpy-proto
#
# What it does:
# 1) Clones SteamDatabase/GameTracking-CS2 (sparse checkout if available)
# 2) Copies ONLY the allowlisted Protobufs/*.proto into ../crates/awpy-proto/proto/
# 3) Reads game/csgo/steam.inf and updates ../crates/awpy-proto/Cargo.toml:
#    - Reads the compatibility epoch MAJOR.MINOR from [package].version
#    - Sets [package].version to (Cargo-safe SemVer with build metadata):
#        MAJOR.MINOR.SourceRevision+ServerVersion
#      The monotonic SourceRevision is the PATCH, so each game build yields a
#      higher, publishable version while MAJOR.MINOR stays the compat epoch.
#      (ClientVersion has always equalled ServerVersion, so only one is kept.)
#
# Environment:
#   CLEAN_DEST=1     delete existing *.proto in DEST_DIR before copying
#   CS2_REF=<ref>    optional: branch/tag/commit to checkout

REPO_URL="https://github.com/SteamDatabase/GameTracking-CS2.git"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Destination for synced protos (relative to this script)
DEST_DIR="$SCRIPT_DIR/../crates/awpy-proto/proto"

# Cargo.toml to update (relative to this script)
CARGO_TOML="$SCRIPT_DIR/../crates/awpy-proto/Cargo.toml"

# Single source of truth for which protos to sync (relative to this script)
MANIFEST="$SCRIPT_DIR/../crates/awpy-proto/proto/allowlist.txt"

CLEAN_DEST="${CLEAN_DEST:-0}"           # 1 to delete existing *.proto in DEST_DIR before copying
CS2_REF="${CS2_REF:-}"                  # optional: branch/tag/commit to checkout

die() { echo "ERROR: $*" >&2; exit 1; }

need_file() { [[ -f "$1" ]] || die "Missing file: $1"; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

need_cmd git
need_file "$CARGO_TOML"
need_file "$MANIFEST"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

REPO_DIR="$TMP_DIR/cs2"
INF_PATH="game/csgo/steam.inf"

has_sparse_checkout() {
  git help -a 2>/dev/null | grep -qE '^\s*sparse-checkout\s*$'
}

clone_repo() {
  if git clone --filter=blob:none --no-checkout "$REPO_URL" "$REPO_DIR" >/dev/null 2>&1; then
    :
  else
    git clone --no-checkout "$REPO_URL" "$REPO_DIR"
  fi

  cd "$REPO_DIR"

  if has_sparse_checkout; then
    git sparse-checkout init --cone >/dev/null 2>&1 || true
    git sparse-checkout set "Protobufs" "$INF_PATH" >/dev/null 2>&1 || true
  fi

  if [[ -n "$CS2_REF" ]]; then
    git checkout -f "$CS2_REF" >/dev/null 2>&1 || die "Failed to checkout CS2_REF=$CS2_REF"
  else
    git checkout -f >/dev/null 2>&1 || die "Failed to checkout repo"
  fi
}

copy_protos() {
  mkdir -p "$DEST_DIR"

  if [[ "$CLEAN_DEST" == "1" ]]; then
    find "$DEST_DIR" -maxdepth 1 -type f -name '*.proto' -delete
  fi

  local copied=0
  while IFS= read -r raw || [[ -n "$raw" ]]; do
    raw="${raw%$'\r'}"              # strip CR for CRLF files

    local line="${raw%%#*}"
    line="$(echo -n "$line" | xargs || true)"
    [[ -z "$line" ]] && continue

    [[ "$line" == *.proto ]] || die "Manifest entry is not a .proto: '$line'"
    [[ "$line" != */* ]] || die "Manifest entry must be a basename (no '/'): '$line'"

    local src="$REPO_DIR/Protobufs/$line"
    [[ -f "$src" ]] || die "Missing proto in upstream: $src"

    cp -f "$src" "$DEST_DIR/"
    copied=$((copied + 1))
  done < "$MANIFEST"

  (( copied > 0 )) || die "Manifest produced 0 files"
  echo "Copied $copied proto files to: $DEST_DIR"
}

parse_steam_inf() {
  local inf_file="$REPO_DIR/$INF_PATH"
  need_file "$inf_file"

  local client server rev
  client="$(grep -E '^ClientVersion=' "$inf_file" | head -n1 | cut -d= -f2 | tr -d '\r')"
  server="$(grep -E '^ServerVersion=' "$inf_file" | head -n1 | cut -d= -f2 | tr -d '\r')"
  rev="$(grep -E '^SourceRevision=' "$inf_file" | head -n1 | cut -d= -f2 | tr -d '\r')"

  [[ "$client" =~ ^[0-9]+$ ]] || die "Invalid ClientVersion: '$client'"
  [[ "$server" =~ ^[0-9]+$ ]] || die "Invalid ServerVersion: '$server'"
  [[ "$rev"    =~ ^[0-9]+$ ]] || die "Invalid SourceRevision: '$rev'"

  echo "$client" "$server" "$rev"
}

extract_version_in_section() {
  local header="$1" toml="$2"
  awk -v header="$header" '
    BEGIN { in_section=0 }
    $0 == "[" header "]" { in_section=1; next }
    $0 ~ /^\[/ {
      if (in_section) exit
    }
    in_section && $0 ~ /^[[:space:]]*version[[:space:]]*=/ {
      if (match($0, /"[^"]+"/)) {
        s = substr($0, RSTART+1, RLENGTH-2)
        print s
        exit
      }
    }
  ' "$toml"
}

update_version_in_section() {
  local header="$1" toml="$2" new_version="$3"
  local tmp
  tmp="$(mktemp)"

  awk -v header="$header" -v new="$new_version" '
    BEGIN { in_section=0; done=0 }
    $0 == "[" header "]" { in_section=1 }
    $0 ~ /^\[/ {
      if (in_section && $0 != "[" header "]") in_section=0
    }
    {
      if (!done && in_section && $0 ~ /^[[:space:]]*version[[:space:]]*=/) {
        if ($0 ~ /"[^"]*"/) {
          sub(/"[^"]*"/, "\"" new "\"")
          done=1
        }
      }
      print
    }
    END {
      if (!done) exit 3
    }
  ' "$toml" > "$tmp" || {
    rm -f "$tmp"
    die "Could not update version in section [$header] in $toml (expected version = \"...\")"
  }

  mv -f "$tmp" "$toml"
}

update_cargo_toml() {
  local client="$1" server="$2" rev="$3"

  # awpy-proto is versioned independently from the workspace release version, so
  # read its current MAJOR.MINOR (the compatibility epoch) from its own [package]
  # section. The existing PATCH is discarded; it is replaced by SourceRevision.
  local current_version
  current_version="$(extract_version_in_section "package" "$CARGO_TOML")"
  [[ -n "$current_version" ]] || die "Could not find quoted version in [package] in $CARGO_TOML"

  if [[ ! "$current_version" =~ ([0-9]+)\.([0-9]+)\. ]]; then
    die "Existing version '$current_version' does not start with MAJOR.MINOR"
  fi

  local major="${BASH_REMATCH[1]}"
  local minor="${BASH_REMATCH[2]}"

  # The suffix keeps only ServerVersion, which has always matched ClientVersion.
  # Warn (don't fail) if they ever diverge, since ClientVersion is then dropped.
  if [[ "$client" != "$server" ]]; then
    echo "WARNING: ClientVersion ($client) != ServerVersion ($server); only ServerVersion is recorded in the version" >&2
  fi

  # build-rev-as-patch: the monotonic SourceRevision becomes the PATCH (so each
  # game build is a higher, publishable version), MAJOR.MINOR stays the
  # compatibility epoch, and ServerVersion rides along as SemVer build metadata.
  local full_version="${major}.${minor}.${rev}+${server}"

  update_version_in_section "package" "$CARGO_TOML" "$full_version"

  echo "Updated $CARGO_TOML ([package].version): -> $full_version"
}

main() {
  clone_repo
  copy_protos

  read -r client server rev < <(parse_steam_inf)
  update_cargo_toml "$client" "$server" "$rev"
}

main "$@"
