set -e
grep -qF "zz_extra_entry" "plugins/hydra_ray_launcher/integration_test_tools/setup_integration_test_ami.py" || { echo "entry missing"; exit 1; }
pytest tools/landscape/test_build_landscape_review.py -q 2>&1 | tail -3
