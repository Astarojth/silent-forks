set -e
test ! -e "scripts/release.py" || { echo "file still present"; exit 1; }
if git grep -n -F "release.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/release.py".bak "scripts/release.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
