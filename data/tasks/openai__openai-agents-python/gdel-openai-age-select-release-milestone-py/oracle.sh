set -e
test ! -e ".github/scripts/select-release-milestone.py" || { echo "file still present"; exit 1; }
if git grep -n -F "select-release-milestone.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls ".github/scripts/select-release-milestone.py".bak ".github/scripts/select-release-milestone.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
