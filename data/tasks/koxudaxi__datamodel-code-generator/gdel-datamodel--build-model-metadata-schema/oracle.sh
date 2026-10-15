set -e
test ! -e "scripts/build_model_metadata_schema.py" || { echo "file still present"; exit 1; }
if git grep -n -F "build_model_metadata_schema.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/build_model_metadata_schema.py".bak "scripts/build_model_metadata_schema.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
