set -e
test ! -e "scripts/generate_resource_docs.py" || { echo "file still present"; exit 1; }
if git grep -n -F "generate_resource_docs.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/generate_resource_docs.py".bak "scripts/generate_resource_docs.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
