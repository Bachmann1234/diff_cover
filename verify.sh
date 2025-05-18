#!/bin/bash
set -euo pipefail
IFS=$'\n\t'
COMPARE_BRANCH=${COMPARE_BRANCH:-origin/main}

black diff_cover tests --check
isort diff_cover tests --check
python -m pytest -n auto --cov-context test --cov --cov-report=xml tests
git fetch origin main:refs/remotes/origin/main
diff-cover --version
diff-quality --version
diff-cover coverage.xml --include-untracked --compare-branch=$COMPARE_BRANCH
diff-quality --violations flake8 --include-untracked --compare-branch=$COMPARE_BRANCH
diff-quality --violations pylint --include-untracked --compare-branch=$COMPARE_BRANCH
doc8 README.rst --ignore D001
