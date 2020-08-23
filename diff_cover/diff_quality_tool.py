"""
Implement the command-line tool interface for diff_quality.
"""

import argparse
import logging
import os
import sys

import pluggy

import diff_cover
from diff_cover import hookspecs
from diff_cover.diff_cover_tool import (
    COMPARE_BRANCH_HELP,
    DIFF_RANGE_NOTATION_HELP,
    FAIL_UNDER_HELP,
    IGNORE_STAGED_HELP,
    IGNORE_UNSTAGED_HELP,
    EXCLUDE_HELP,
    HTML_REPORT_HELP,
    CSS_FILE_HELP,
    IGNORE_WHITESPACE,
)
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.report_generator import (
    HtmlQualityReportGenerator,
    StringQualityReportGenerator,
)
from diff_cover.violationsreporters.base import QualityReporter
from diff_cover.violationsreporters.violations_reporter import (
    CppcheckDriver,
    flake8_driver,
    pyflakes_driver,
    PylintDriver,
    jshint_driver,
    eslint_driver,
    pydocstyle_driver,
    pycodestyle_driver,
)
from diff_cover.violationsreporters.java_violations_reporter import (
    CheckstyleXmlDriver,
    checkstyle_driver,
    FindbugsXmlDriver,
    PmdXmlDriver,
)

QUALITY_DRIVERS = {
    "cppcheck": CppcheckDriver(),
    "pycodestyle": pycodestyle_driver,
    "pyflakes": pyflakes_driver,
    "pylint": PylintDriver(),
    "flake8": flake8_driver,
    "jshint": jshint_driver,
    "eslint": eslint_driver,
    "pydocstyle": pydocstyle_driver,
    "checkstyle": checkstyle_driver,
    "checkstylexml": CheckstyleXmlDriver(),
    "findbugs": FindbugsXmlDriver(),
    "pmd": PmdXmlDriver(),
}

VIOLATION_CMD_HELP = "Which code quality tool to use (%s)" % "/".join(
    sorted(QUALITY_DRIVERS)
)
INPUT_REPORTS_HELP = "Which violations reports to use"
OPTIONS_HELP = "Options to be passed to the violations tool"


LOGGER = logging.getLogger(__name__)


def parse_quality_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'violations': pycodestyle| pyflakes | flake8 | pylint | ...,
            'html_report': None | HTML_REPORT,
            'external_css_file': None | CSS_FILE,
        }

    where `HTML_REPORT` and `CSS_FILE` are paths.
    """
    parser = argparse.ArgumentParser(description=diff_cover.QUALITY_DESCRIPTION)

    parser.add_argument(
        "--violations", metavar="TOOL", type=str, help=VIOLATION_CMD_HELP, required=True
    )

    parser.add_argument(
        "--html-report",
        metavar="FILENAME",
        type=str,
        default=None,
        help=HTML_REPORT_HELP,
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
        "input_reports", type=str, nargs="*", default=[], help=INPUT_REPORTS_HELP
    )

    parser.add_argument(
        "--options", type=str, nargs="?", default=None, help=OPTIONS_HELP
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
        "--diff-range-notation",
        metavar="RANGE_NOTATION",
        type=str,
        default="...",
        help=DIFF_RANGE_NOTATION_HELP,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="diff-quality {}".format(diff_cover.VERSION),
    )
    parser.add_argument(
        "--ignore-whitespace",
        action="store_true",
        default=False,
        help=IGNORE_WHITESPACE,
    )

    return vars(parser.parse_args(argv))


def generate_quality_report(
    tool,
    compare_branch,
    html_report=None,
    css_file=None,
    ignore_staged=False,
    ignore_unstaged=False,
    exclude=None,
    diff_range_notation=None,
    ignore_whitespace=False,
):
    """
    Generate the quality report, using kwargs from `parse_args()`.
    """
    supported_extensions = (
        getattr(tool, "supported_extensions", None) or tool.driver.supported_extensions
    )
    diff = GitDiffReporter(
        compare_branch,
        git_diff=GitDiffTool(diff_range_notation, ignore_whitespace),
        ignore_staged=ignore_staged,
        ignore_unstaged=ignore_unstaged,
        supported_extensions=supported_extensions,
        exclude=exclude,
    )

    if html_report is not None:
        css_url = css_file
        if css_url is not None:
            css_url = os.path.relpath(css_file, os.path.dirname(html_report))
        reporter = HtmlQualityReportGenerator(tool, diff, css_url=css_url)
        with open(html_report, "wb") as output_file:
            reporter.generate_report(output_file)
        if css_file is not None:
            with open(css_file, "wb") as output_file:
                reporter.generate_css(output_file)

    # Generate the report for stdout
    reporter = StringQualityReportGenerator(tool, diff)
    output_file = sys.stdout.buffer

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
    arg_dict = parse_quality_args(argv[1:])
    GitPathTool.set_cwd(directory)
    fail_under = arg_dict.get("fail_under")
    tool = arg_dict["violations"]
    user_options = arg_dict.get("options")
    if user_options:
        # strip quotes if present
        first_char = user_options[0]
        last_char = user_options[-1]
        if first_char == last_char and first_char in ('"', "'"):
            user_options = user_options[1:-1]
    reporter = None
    driver = QUALITY_DRIVERS.get(tool)
    if driver is None:
        # The requested tool is not built into diff_cover. See if another Python
        # package provides it.
        pm = pluggy.PluginManager("diff_cover")
        pm.add_hookspecs(hookspecs)
        pm.load_setuptools_entrypoints("diff_cover")
        for hookimpl in pm.hook.diff_cover_report_quality.get_hookimpls():
            if hookimpl.plugin_name == tool:
                reporter = hookimpl.function()
                break

    if reporter or driver:
        input_reports = []
        try:
            if driver is not None:
                # If we've been given pre-generated reports,
                # try to open the files

                for path in arg_dict["input_reports"]:
                    try:
                        input_reports.append(open(path, "rb"))
                    except OSError:
                        LOGGER.warning("Could not load '{}'".format(path))
                reporter = QualityReporter(driver, input_reports, user_options)

            percent_passing = generate_quality_report(
                reporter,
                arg_dict["compare_branch"],
                html_report=arg_dict["html_report"],
                css_file=arg_dict["external_css_file"],
                ignore_staged=arg_dict["ignore_staged"],
                ignore_unstaged=arg_dict["ignore_unstaged"],
                exclude=arg_dict["exclude"],
                diff_range_notation=arg_dict["diff_range_notation"],
                ignore_whitespace=arg_dict["ignore_whitespace"],
            )
            if percent_passing >= fail_under:
                return 0
            else:
                LOGGER.error("Failure. Quality is below {}%.".format(fail_under))
                return 1

        except ImportError:
            LOGGER.error("Quality tool not installed: '{}'".format(tool))
            return 1
        except OSError as exc:
            LOGGER.error("Failure: '{}'".format(exc))
            return 1
        # Close any reports we opened
        finally:
            for file_handle in input_reports:
                file_handle.close()

    else:
        LOGGER.error("Quality tool not recognized: '{}'".format(tool))
        return 1


if __name__ == "__main__":
    sys.exit(main())
