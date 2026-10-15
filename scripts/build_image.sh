#!/bin/bash
# build_image.sh owner__repo  -> forkdpo-run:owner__repo (builds the base image first if missing)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
key="$1"; recipe="$ROOT/data/environments/$key"
[ -f "$recipe/Dockerfile" ] || { echo "no recipe for $key" >&2; exit 1; }
task=$(ls "$ROOT"/data/tasks/"$key"/*/task.json | head -1)
repo=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['repo'])" "$task")
commit=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['base_commit'])" "$task")
base=$(sed -n 's/^FROM forkdpo-base:\(.*\)$/\1/p' "$recipe/Dockerfile")
if ! docker image inspect "forkdpo-base:$base" >/dev/null 2>&1; then
  docker build --platform linux/amd64 -t "forkdpo-base:$base" -f "$ROOT/data/environments/bases/Dockerfile_$base" "$ROOT/data/environments/bases"
fi
bash "$ROOT/scripts/clone_repo.sh" "$repo" "$commit"
ctx="$ROOT/env/$key"
cp "$recipe"/install.sh "$ctx"/
[ -f "$recipe/extra_install.sh" ] && cp "$recipe/extra_install.sh" "$ctx"/
docker build --platform linux/amd64 -t "forkdpo-run:$key" -f "$recipe/Dockerfile" "$ctx"
