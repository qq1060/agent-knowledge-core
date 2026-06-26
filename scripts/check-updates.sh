#!/usr/bin/env bash
# Check for upstream updates to external skills.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/manifests/skills.json"
LOCKFILE="$ROOT/manifests/skills.lock.json"

QUIET=false
NAMES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet) QUIET=true; shift ;;
    --name)
      if [[ $# -lt 2 ]]; then
        echo "error: --name requires a value" >&2
        exit 2
      fi
      NAMES+=("$2")
      shift 2
      ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--quiet] [--name <skill>]..."
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$MANIFEST" ]]; then
  echo "error: $MANIFEST not found" >&2
  exit 2
fi

read_skills_py='
import json, sys

manifest = json.load(open(sys.argv[1]))
try:
    lock = json.load(open(sys.argv[2]))
except FileNotFoundError:
    lock = {"locked": {}}

names = set(sys.argv[3:]) if len(sys.argv) > 3 else set()
locked = lock.get("locked", {})

for item in manifest.get("skills", []):
    if item.get("kind") != "external":
        continue
    name = item.get("name", "")
    if names and name not in names:
        continue
    source = item.get("source", "")
    ref = item.get("ref", "main")
    entry = locked.get(name, {})
    commit = entry.get("resolved_commit", "")
    print("%s\t%s\t%s\t%s" % (name, source, ref, commit))
'

_TMPDIR="${TMPDIR:-/tmp}"
SKILL_DATA="$(mktemp "$_TMPDIR/ak-check.XXXXXX")"
CACHE_FILE="$(mktemp "$_TMPDIR/ak-cache.XXXXXX")"
trap 'rm -f "$SKILL_DATA" "$CACHE_FILE"' EXIT

python3 -c "$read_skills_py" "$MANIFEST" "$LOCKFILE" ${NAMES[@]+"${NAMES[@]}"} > "$SKILL_DATA"

if [[ ! -s "$SKILL_DATA" ]]; then
  $QUIET || echo "no external skills to check"
  exit 0
fi

source_to_url() {
  local src="$1"
  if [[ "$src" == github:* ]]; then
    echo "https://github.com/${src#github:}.git"
  else
    echo "$src"
  fi
}

resolve_ref() {
  local url="$1" ref="$2"
  local patterns=()
  local ref_lower
  ref_lower="$(printf '%s' "$ref" | tr '[:upper:]' '[:lower:]')"
  if [[ "$ref_lower" == "head" || -z "$ref" ]]; then
    patterns=(HEAD)
  else
    patterns=("$ref" "refs/heads/$ref" "refs/tags/$ref^{}" "refs/tags/$ref")
  fi
  local output
  output="$(git ls-remote "$url" "${patterns[@]}" 2>/dev/null)" || true
  [[ -z "$output" ]] && return
  local pat commit
  for pat in "${patterns[@]}"; do
    commit="$(awk -v p="$pat" '$2 == p { print $1; exit }' <<< "$output")"
    if [[ -n "$commit" ]]; then
      echo "$commit"
      return
    fi
  done
}

cache_get() {
  awk -F'\t' -v k="$1" '$1 == k { print $2; found=1; exit } END { if (!found) print "" }' "$CACHE_FILE"
}

cache_put() {
  printf '%s\t%s\n' "$1" "$2" >> "$CACHE_FILE"
}

while IFS=$'\t' read -r _name source ref _commit; do
  key="${source}:${ref}"
  cached="$(cache_get "$key")"
  if [[ -z "$cached" ]]; then
    url="$(source_to_url "$source")"
    remote_commit="$(resolve_ref "$url" "$ref")"
    if [[ -z "$remote_commit" ]]; then
      cache_put "$key" "UNKNOWN"
    else
      cache_put "$key" "$remote_commit"
    fi
  fi
done < "$SKILL_DATA"

has_updates=false
while IFS=$'\t' read -r name source ref locked_commit; do
  key="${source}:${ref}"
  remote="$(cache_get "$key")"
  if [[ "$remote" == "UNKNOWN" ]]; then
    $QUIET || echo "[?]  $name  (could not reach ${source} ${ref})"
    continue
  fi
  if [[ -z "$locked_commit" ]]; then
    has_updates=true
    $QUIET || echo "[!]  $name  not locked; remote=${remote:0:12}"
  elif [[ "$locked_commit" != "$remote" ]]; then
    has_updates=true
    $QUIET || echo "[!]  $name  locked=${locked_commit:0:12}  remote=${remote:0:12}"
  else
    $QUIET || echo "[ok] $name  ${locked_commit:0:12}"
  fi
done < "$SKILL_DATA"

if $has_updates; then
  $QUIET || echo
  $QUIET || echo "Run 'ak-core fetch --name <skill>' to update."
  exit 1
fi

$QUIET || echo
$QUIET || echo "All checked skills are current."
