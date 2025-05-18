#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

ruff format --check
ruff check --select I
python -m pytest -n auto --cov-context test --cov --cov-report=xml tests
git fetch origin main:refs/remotes/origin/main
diff-cover --version
diff-quality --version
diff-cover coverage.xml --include-untracked --compare-branch=$COMPARE_BRANCH
diff-quality --violations ruff.check --include-untracked --compare-branch=$COMPARE_BRANCH
doc8 README.rst --ignore D001

