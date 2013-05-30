diff-cover
==========

Automatically find diff lines that need test coverage.

Usage:

    diff-cover COVERAGE_XML --git-branch BRANCH [--html-report REPORT.html]

This will compare the current git branch to `BRANCH`, identify lines
that are not covered (based on `COVERAGE_XML`), and (optionally) generate an HTML report.

`diff-cover` ignores files not referenced in `COVERAGE_XML`, since these files
are not tested.  This means that documentation and configuration changes
will be ignored.

If `--html-report` is not specified, `diff-cover` prints a text report
to stdout.
