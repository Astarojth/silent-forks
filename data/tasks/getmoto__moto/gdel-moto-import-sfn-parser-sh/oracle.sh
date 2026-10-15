set -e
test ! -e "scripts/import_sfn_parser.sh" || { echo "file still present"; exit 1; }
if git grep -n -F "import_sfn_parser.sh" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/import_sfn_parser.sh".bak "scripts/import_sfn_parser.sh".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
