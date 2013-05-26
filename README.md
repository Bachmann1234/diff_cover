diff-cover
==========

Automatically find diff lines that need test coverage.

Usage:

    diff_cover --git-branch BRANCH --coverage-xml COVERAGE_XML [--html-report REPORT.html]

This will compare the current git branch to `BRANCH`, identify lines
that are not covered (based on `COVERAGE_XML`), and (optionally) generate an HTML report.

`diff_cover` ignores files not referenced in `COVERAGE_XML`, since these files
are not tested.  This means that documentation and configuration changes
will be ignored.

If `--html-report` is not specified, `diff_cover` prints a text report
to stdout.
