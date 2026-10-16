#!/usr/bin/env bash
# Checks and finalization for the manual package release workflow.
set -euo pipefail

check_tag() {
  local response commit
  if response=$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$TAG_NAME" --jq .object.sha 2>&1); then
    # Resolve annotated tags to their commit as well as lightweight tags.
    commit=$(gh api "repos/$GITHUB_REPOSITORY/commits/$TAG_NAME" --jq .sha)
    if [ "$commit" != "$GITHUB_SHA" ]; then
      echo "$TAG_NAME points at $commit; refusing to move it." >&2
      exit 1
    fi
    return 0
  elif printf '%s\n' "$response" | grep -q 'HTTP 404'; then
    return 1
  else
    printf '%s\n' "$response" >&2
    exit 1
  fi
}

case "${1:-}" in
  check)
    if [ "$GITHUB_REF" != refs/heads/main ]; then
      echo "Run releases from main (got $GITHUB_REF)." >&2
      exit 1
    fi

    result=$(gh api "repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA/check-runs" \
      --jq '.check_runs[] | select(.name == "CI Check") | .conclusion')
    if [ "$result" != success ]; then
      echo "CI Check has not passed on $GITHUB_SHA (result: ${result:-not found})." >&2
      exit 1
    fi

    metadata=$(cargo metadata --locked --no-deps --format-version 1)
    version=$(printf '%s' "$metadata" | jq -er --arg package "$PACKAGE" \
      '.packages[] | select(.name == $package) | .version')
    if [ "$version" != "$REQUESTED_VERSION" ]; then
      echo "Requested $PACKAGE $REQUESTED_VERSION, but Cargo.toml contains $version." >&2
      exit 1
    fi

    case "$PACKAGE" in
      awpy) title=Awpy; dependency=awpy-proto ;;
      awpy-proto) title=awpy-proto; dependency= ;;
      awpy-python) title='Awpy Python'; dependency=awpy ;;
      *) echo "Unknown release package: $PACKAGE" >&2; exit 1 ;;
    esac
    if [ -n "$dependency" ]; then
      required_version=$(printf '%s' "$metadata" | jq -er --arg package "$dependency" \
        '.packages[] | select(.name == $package) | .version')
      encoded_version=$(printf '%s' "$required_version" | jq -sRr @uri)
      status=$(curl -sSL --retry 3 -A awpy-release-ci -o /dev/null -w '%{http_code}' \
        "https://crates.io/api/v1/crates/$dependency/$encoded_version")
      case "$status" in
        200) ;;
        404) echo "Release $dependency $required_version first." >&2; exit 1 ;;
        *) echo "Could not check $dependency publication (HTTP $status)." >&2; exit 1 ;;
      esac
    fi
    TAG_NAME="$PACKAGE-v$version"
    if check_tag; then
      echo "$TAG_NAME already points at $GITHUB_SHA."
    fi
    printf 'version=%s\ntag=%s\nrelease_title=%s %s\n' \
      "$version" "$TAG_NAME" "$title" "$version" >> "$GITHUB_OUTPUT"
    ;;

  finalize)
    if ! check_tag; then
      gh api "repos/$GITHUB_REPOSITORY/git/refs" \
        -f ref="refs/tags/$TAG_NAME" -f sha="$GITHUB_SHA" > /dev/null
    fi
    if response=$(gh api "repos/$GITHUB_REPOSITORY/releases/tags/$TAG_NAME" 2>&1); then
      echo "GitHub release $TAG_NAME already exists; skipping."
      exit 0
    elif ! printf '%s\n' "$response" | grep -q 'HTTP 404'; then
      printf '%s\n' "$response" >&2
      exit 1
    fi

    notes_file=".github/release-notes/$TAG_NAME.md"
    if [ -f "$notes_file" ]; then
      notes=(--notes-file "$notes_file")
    else
      notes=(--generate-notes)
    fi
    gh release create "$TAG_NAME" --verify-tag --title "$RELEASE_TITLE" \
      --repo "$GITHUB_REPOSITORY" "${notes[@]}"
    ;;

  *) echo "Usage: $0 check|finalize" >&2; exit 1 ;;
esac
