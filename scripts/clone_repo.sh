#!/bin/bash
# clone_repo.sh owner/name commit  -> env/<owner__name>/src at that commit
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
repo="$1"; commit="$2"; d="$ROOT/env/${repo//\//__}"
mkdir -p "$d"
if [ ! -d "$d/src/.git" ]; then git clone -q "https://github.com/$repo.git" "$d/src"; fi
git -C "$d/src" fetch -q origin "$commit" 2>/dev/null || true
git -C "$d/src" checkout -q -f "$commit"
echo "$repo at $(git -C "$d/src" rev-parse --short HEAD) $(git -C "$d/src" log -1 --format=%cs)"
