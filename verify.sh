#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

black diff_cover tests --check
isort diff_cover tests --check
python -m pytest --cov --cov-report=xml tests
git fetch origin main:refs/remotes/origin/main
diff-cover --version
diff-quality --version
diff-cover coverage.xml --include-untracked
diff-quality --violations flake8 --include-untracked
diff-quality --violations pylint --include-untracked
doc8 README.rst --ignore D001

