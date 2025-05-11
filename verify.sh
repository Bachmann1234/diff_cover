#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

black diff_cover tests
isort diff_cover tests
python -m pytest -n auto --cov-context test --cov --cov-report=xml tests --cov-report=html --cov-report=term
git fetch origin main:refs/remotes/origin/main
diff-cover --version
diff-quality --version
diff-cover coverage.xml --include-untracked
diff-quality --violations flake8 --include-untracked
diff-quality --violations pylint --include-untracked
doc8 README.rst --ignore D001

