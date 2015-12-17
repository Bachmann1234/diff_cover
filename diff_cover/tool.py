"""
Implement the command-line tool interface.
"""
from __future__ import unicode_literals
import argparse
import os
import sys
from xml.etree import cElementTree
import diff_cover
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.violations_reporter import (
    XmlCoverageReporter, Pep8QualityReporter,
    PyflakesQualityReporter, PylintQualityReporter,
    Flake8QualityReporter, JsHintQualityReporter
)
from diff_cover.report_generator import (
    HtmlReportGenerator, StringReportGenerator,
    HtmlQualityReportGenerator, StringQualityReportGenerator
)
import six

COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"
COMPARE_BRANCH_HELP = "Branch to compare"
VIOLATION_CMD_HELP = "Which code quality tool to use"
INPUT_REPORTS_HELP = "Pep8, pyflakes, flake8, or pylint reports to use"
OPTIONS_HELP = "Options to be passed to the violations tool"
FAIL_UNDER_HELP = "Returns an error code if coverage or quality score is below this value"
IGNORE_UNSTAGED_HELP = "Ignores unstaged changes"

QUALITY_REPORTERS = {
    'pep8': Pep8QualityReporter,
    'pyflakes': PyflakesQualityReporter,
    'pylint': PylintQualityReporter,
    'flake8': Flake8QualityReporter,
    'jshint': JsHintQualityReporter,
}


import logging
logging.basicConfig(format='%(message)s')
LOGGER = logging.getLogger(__name__)


def parse_coverage_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'coverage_xml': COVERAGE_XML,
            'html_report': None | HTML_REPORT
        }

    where `COVERAGE_XML` is a path, and `HTML_REPORT` is a path.

    The path strings may or may not exist.
    """
    parser = argparse.ArgumentParser(description=diff_cover.DESCRIPTION)

    parser.add_argument(
        'coverage_xml',
        type=str,
        help=COVERAGE_XML_HELP,
        nargs='+'
    )

    parser.add_argument(
        '--html-report',
        type=str,
        default=None,
        help=HTML_REPORT_HELP
    )

    parser.add_argument(
        '--compare-branch',
        type=str,
        default='origin/master',
        help=COMPARE_BRANCH_HELP
    )

    parser.add_argument(
        '--fail-under',
        type=float,
        default='0',
        help=FAIL_UNDER_HELP
    )

    parser.add_argument(
        '--ignore-unstaged',
        action='store_true',
        default=False,
        help=IGNORE_UNSTAGED_HELP
    )

    return vars(parser.parse_args(argv))


def parse_quality_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'violations': pep8 | pyflakes | flake8 | pylint
            'html_report': None | HTML_REPORT
        }

    where `HTML_REPORT` is a path.
    """
    parser = argparse.ArgumentParser(
        description=diff_cover.QUALITY_DESCRIPTION
    )

    parser.add_argument(
        '--violations',
        type=str,
        help=VIOLATION_CMD_HELP,
        required=True
    )

    parser.add_argument(
        '--html-report',
        type=str,
        default=None,
        help=HTML_REPORT_HELP
    )

    parser.add_argument(
        '--compare-branch',
        type=str,
        default='origin/master',
        help=COMPARE_BRANCH_HELP
    )

    parser.add_argument(
        'input_reports',
        type=str,
        nargs="*",
        default=[],
        help=INPUT_REPORTS_HELP
    )

    parser.add_argument(
        '--options',
        type=str,
        nargs='?',
        default=None,
        help=OPTIONS_HELP
    )

    parser.add_argument(
        '--fail-under',
        type=float,
        default='0',
        help=FAIL_UNDER_HELP
    )

    parser.add_argument(
        '--ignore-unstaged',
        action='store_true',
        default=False,
        help=IGNORE_UNSTAGED_HELP
    )

    return vars(parser.parse_args(argv))


def generate_coverage_report(coverage_xml, compare_branch, html_report=None, ignore_unstaged=False):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool(), ignore_unstaged=ignore_unstaged)

    xml_roots = [cElementTree.parse(xml_root) for xml_root in coverage_xml]
    coverage = XmlCoverageReporter(xml_roots)

    # Build a report generator
    if html_report is not None:
        reporter = HtmlReportGenerator(coverage, diff)
        with open(html_report, "wb") as output_file:
            reporter.generate_report(output_file)

    reporter = StringReportGenerator(coverage, diff)
    output_file = sys.stdout if six.PY2 else sys.stdout.buffer

    # Generate the report
    reporter.generate_report(output_file)
    return reporter.total_percent_covered()


def generate_quality_report(tool, compare_branch, html_report=None, ignore_unstaged=False):
    """
    Generate the quality report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool(), ignore_unstaged=ignore_unstaged)

    if html_report is not None:
        reporter = HtmlQualityReportGenerator(tool, diff)
        with open(html_report, "wb") as output_file:
            reporter.generate_report(output_file)

    # Generate the report for stdout
    reporter = StringQualityReportGenerator(tool, diff)
    output_file = sys.stdout if six.PY2 else sys.stdout.buffer

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
    argv = argv or sys.argv
    # Init the path tool to work with the specified directory,
    # or the current directory if it isn't set.
    if not directory:
        try:
            directory = os.getcwdu()
        except AttributeError:
            directory = os.getcwd()

    progname = argv[0]
    filename = os.path.basename(progname)
    name, _ = os.path.splitext(filename)

    GitPathTool.set_cwd(directory)

    if 'diff-cover' in name:
        arg_dict = parse_coverage_args(argv[1:])
        fail_under = arg_dict.get('fail_under')
        percent_covered = generate_coverage_report(
            arg_dict['coverage_xml'],
            arg_dict['compare_branch'],
            html_report=arg_dict['html_report'],
            ignore_unstaged=arg_dict['ignore_unstaged'],
        )

        if percent_covered >= fail_under:
            return 0
        else:
            LOGGER.error("Failure. Coverage is below {0}%.".format(fail_under))
            return 1

    elif 'diff-quality' in name:
        arg_dict = parse_quality_args(argv[1:])
        fail_under = arg_dict.get('fail_under')
        tool = arg_dict['violations']
        user_options = arg_dict.get('options')
        if user_options:
            # strip quotes if present
            first_char = user_options[0]
            last_char = user_options[-1]
            if first_char == last_char and first_char in ('"', "'"):
                user_options = user_options[1:-1]
        reporter_class = QUALITY_REPORTERS.get(tool)

        if reporter_class is not None:
            # If we've been given pre-generated reports,
            # try to open the files
            input_reports = []

            for path in arg_dict['input_reports']:
                try:
                    input_reports.append(open(path, 'rb'))
                except IOError:
                    LOGGER.warning("Could not load '{0}'".format(path))
            try:
                reporter = reporter_class(tool, input_reports, user_options=user_options)
                percent_passing = generate_quality_report(
                    reporter,
                    arg_dict['compare_branch'],
                    arg_dict['html_report'],
                    arg_dict['ignore_unstaged'],
                )
                if percent_passing >= fail_under:
                    return 0
                else:
                    LOGGER.error("Failure. Quality is below {0}%.".format(fail_under))
                    return 1

            except (ImportError, EnvironmentError):
                LOGGER.error(
                    "Quality tool not installed: '{0}'".format(tool)
                )
                return 1
            # Close any reports we opened
            finally:
                for file_handle in input_reports:
                    file_handle.close()

        else:
            LOGGER.error("Quality tool not recognized: '{0}'".format(tool))
            return 1

    else:
        assert False, 'Expect diff-cover or diff-quality in {0}'.format(name)

if __name__ == "__main__":
    exit(main())
