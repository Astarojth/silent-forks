set -e
test -z "$(git status --porcelain --untracked-files=no)" && echo "tree clean" || { git status --porcelain | head; exit 1; }
