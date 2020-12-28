import logging

import os
import sys
import argparse

try:
    # Needed for Python < 3.3, works up to 3.8
    import xml.etree.cElementTree as etree
except ImportError:
    # Python 3.9 onwards
    import xml.etree.ElementTree as etree

from diff_cover import DESCRIPTION, VERSION
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.report_generator import (
    HtmlReportGenerator,
    StringReportGenerator,
    JsonReportGenerator,
    MarkdownReportGenerator,
)
from diff_cover.violationsreporters.violations_reporter import XmlCoverageReporter

HTML_REPORT_HELP = "Diff coverage HTML output"
JSON_REPORT_HELP = "Diff coverage JSON output"
MARKDOWN_REPORT_HELP = "Diff coverage Markdown output"
COMPARE_BRANCH_HELP = "Branch to compare"
CSS_FILE_HELP = "Write CSS into an external file"
FAIL_UNDER_HELP = (
    "Returns an error code if coverage or quality score is below this value"
)
IGNORE_STAGED_HELP = "Ignores staged changes"
IGNORE_UNSTAGED_HELP = "Ignores unstaged changes"
IGNORE_WHITESPACE = "When getting a diff ignore any and all whitespace"
EXCLUDE_HELP = "Exclude files, more patterns supported"
SRC_ROOTS_HELP = "List of source directories (only for jacoco coverage reports)"
COVERAGE_XML_HELP = "XML coverage report"
DIFF_RANGE_NOTATION_HELP = (
    "Git diff range notation to use when comparing branches, defaults to '...'"
)

LOGGER = logging.getLogger(__name__)


def parse_coverage_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'coverage_xml': COVERAGE_XML,
            'html_report': None | HTML_REPORT,
            'json_report': None | JSON_REPORT,
            'external_css_file': None | CSS_FILE,
        }

    where `COVERAGE_XML`, `HTML_REPORT`, `JSON_REPORT`, and `CSS_FILE` are paths.

    The path strings may or may not exist.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument("coverage_xml", type=str, help=COVERAGE_XML_HELP, nargs="+")

    output_format = parser.add_mutually_exclusive_group()

    output_format.add_argument(
        "--html-report",
        metavar="FILENAME",
        type=str,
        default=None,
        help=HTML_REPORT_HELP,
    )

    output_format.add_argument(
        "--json-report",
        metavar="FILENAME",
        type=str,
        default=None,
        help=JSON_REPORT_HELP,
    )

    output_format.add_argument(
        "--markdown-report",
        metavar="FILENAME",
        type=str,
        default=None,
        help=MARKDOWN_REPORT_HELP,
    )

    parser.add_argument(
        "--external-css-file",
        metavar="FILENAME",
        type=str,
        default=None,
        help=CSS_FILE_HELP,
    )

    parser.add_argument(
        "--compare-branch",
        metavar="BRANCH",
        type=str,
        default="origin/master",
        help=COMPARE_BRANCH_HELP,
    )

    parser.add_argument(
        "--fail-under", metavar="SCORE", type=float, default="0", help=FAIL_UNDER_HELP
    )

    parser.add_argument(
        "--ignore-staged", action="store_true", default=False, help=IGNORE_STAGED_HELP
    )

    parser.add_argument(
        "--ignore-unstaged",
        action="store_true",
        default=False,
        help=IGNORE_UNSTAGED_HELP,
    )

    parser.add_argument(
        "--exclude", metavar="EXCLUDE", type=str, nargs="+", help=EXCLUDE_HELP
    )

    parser.add_argument(
        "--src-roots",
        metavar="DIRECTORY",
        type=str,
        nargs="+",
        default=["src/main/java", "src/test/java"],
        help=SRC_ROOTS_HELP,
    )

    parser.add_argument(
        "--diff-range-notation",
        metavar="RANGE_NOTATION",
        type=str,
        default="...",
        choices=["...", ".."],
        help=DIFF_RANGE_NOTATION_HELP,
    )

    parser.add_argument(
        "--version", action="version", version="diff-cover {}".format(VERSION)
    )

    parser.add_argument(
        "--ignore-whitespace",
        action="store_true",
        default=False,
        help=IGNORE_WHITESPACE,
    )

    return vars(parser.parse_args(argv))


def generate_coverage_report(
    coverage_xml,
    compare_branch,
    html_report=None,
    css_file=None,
    json_report=None,
    markdown_report=None,
    ignore_staged=False,
    ignore_unstaged=False,
    exclude=None,
    src_roots=None,
    diff_range_notation=None,
    ignore_whitespace=False,
):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(
        compare_branch,
        git_diff=GitDiffTool(diff_range_notation, ignore_whitespace),
        ignore_staged=ignore_staged,
        ignore_unstaged=ignore_unstaged,
        exclude=exclude,
    )

    xml_roots = [etree.parse(xml_root) for xml_root in coverage_xml]
    coverage = XmlCoverageReporter(xml_roots, src_roots)

    # Build a report generator
    if html_report is not None:
        css_url = css_file
        if css_url is not None:
            css_url = os.path.relpath(css_file, os.path.dirname(html_report))
        reporter = HtmlReportGenerator(coverage, diff, css_url=css_url)
        with open(html_report, "wb") as output_file:
            reporter.generate_report(output_file)
        if css_file is not None:
            with open(css_file, "wb") as output_file:
                reporter.generate_css(output_file)

    elif json_report is not None:
        reporter = JsonReportGenerator(coverage, diff)
        with open(json_report, "wb") as output_file:
            reporter.generate_report(output_file)

    elif markdown_report is not None:
        reporter = MarkdownReportGenerator(coverage, diff)
        with open(markdown_report, "wb") as output_file:
            reporter.generate_report(output_file)

    reporter = StringReportGenerator(coverage, diff)
    output_file = sys.stdout.buffer

    # Generate the report
    reporter.generate_report(output_file)
    return reporter.total_percent_covered()


def main(argv=None, directory=None):
    """
    Main entry point for the tool, used by setup.py
    Returns a value that can be passed into exit() specifying
    the exit code.
    1 is an error
    0 is successful run
    """
    logging.basicConfig(format="%(message)s")

    argv = argv or sys.argv
    arg_dict = parse_coverage_args(argv[1:])
    GitPathTool.set_cwd(directory)
    fail_under = arg_dict.get("fail_under")
    percent_covered = generate_coverage_report(
        arg_dict["coverage_xml"],
        arg_dict["compare_branch"],
        html_report=arg_dict["html_report"],
        json_report=arg_dict["json_report"],
        markdown_report=arg_dict["markdown_report"],
        css_file=arg_dict["external_css_file"],
        ignore_staged=arg_dict["ignore_staged"],
        ignore_unstaged=arg_dict["ignore_unstaged"],
        exclude=arg_dict["exclude"],
        src_roots=arg_dict["src_roots"],
        diff_range_notation=arg_dict["diff_range_notation"],
        ignore_whitespace=arg_dict["ignore_whitespace"],
    )

    if percent_covered >= fail_under:
        return 0
    else:
        LOGGER.error("Failure. Coverage is below {}%.".format(fail_under))
        return 1


if __name__ == "__main__":
    sys.exit(main())
