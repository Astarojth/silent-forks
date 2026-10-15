set -e
test ! -e "scripts/github_client.py" || { echo "file still present"; exit 1; }
if git grep -n -F "github_client.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/github_client.py".bak "scripts/github_client.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
