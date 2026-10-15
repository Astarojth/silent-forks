set -e
test ! -e "scripts/check_pre_commit_rev_in_example.py" || { echo "file still present"; exit 1; }
if git grep -n -F "check_pre_commit_rev_in_example.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/check_pre_commit_rev_in_example.py".bak "scripts/check_pre_commit_rev_in_example.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
