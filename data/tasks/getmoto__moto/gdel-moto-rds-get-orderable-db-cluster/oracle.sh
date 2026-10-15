set -e
test ! -e "scripts/rds_get_orderable_db_cluster_options.py" || { echo "file still present"; exit 1; }
if git grep -n -F "rds_get_orderable_db_cluster_options.py" -- . 2>/dev/null | head -3 | grep .; then echo "dangling reference"; exit 1; fi
if ls "scripts/rds_get_orderable_db_cluster_options.py".bak "scripts/rds_get_orderable_db_cluster_options.py".orig 2>/dev/null | grep .; then echo "backup left"; exit 1; fi
echo removed
