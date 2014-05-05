"""
Implement the command-line tool interface.
"""
from __future__ import unicode_literals
import argparse
import os
import sys
import diff_cover
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.violations_reporter import (
    XmlCoverageReporter, Pep8QualityReporter, PylintQualityReporter
)
from diff_cover.report_generator import (
    HtmlReportGenerator, StringReportGenerator,
    HtmlQualityReportGenerator, StringQualityReportGenerator
)
from lxml import etree

COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"
COMPARE_BRANCH_HELP = "Branch to compare"
VIOLATION_CMD_HELP = "Which code quality tool to use"
INPUT_REPORTS_HELP = "Pep8 or pylint reports to use"

QUALITY_REPORTERS = {
    'pep8': Pep8QualityReporter,
    'pylint': PylintQualityReporter
}


import logging
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

    return vars(parser.parse_args(argv))


def parse_quality_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'violations': pep8 | pylint
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

    return vars(parser.parse_args(argv))


def generate_coverage_report(coverage_xml, compare_branch, html_report=None):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool())

    xml_roots = [etree.parse(xml_root) for xml_root in coverage_xml]
    git_path = GitPathTool(os.getcwd())
    coverage = XmlCoverageReporter(xml_roots, git_path)

    # Build a report generator
    if html_report is not None:
        reporter = HtmlReportGenerator(coverage, diff)
        output_file = open(html_report, "w")
    else:
        reporter = StringReportGenerator(coverage, diff)
        output_file = sys.stdout

    # Generate the report
    reporter.generate_report(output_file)


def generate_quality_report(tool, compare_branch, html_report=None):
    """
    Generate the quality report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(compare_branch, git_diff=GitDiffTool())

    if html_report is not None:
        reporter = HtmlQualityReportGenerator(tool, diff)
        output_file = open(html_report, "w")
    else:
        reporter = StringQualityReportGenerator(tool, diff)
        output_file = sys.stdout

    reporter.generate_report(output_file)


def main():
    """
    Main entry point for the tool, used by setup.py
    """
    progname = sys.argv[0]

    if progname.endswith('diff-cover'):
        arg_dict = parse_coverage_args(sys.argv[1:])
        generate_coverage_report(
            arg_dict['coverage_xml'],
            arg_dict['compare_branch'],
            html_report=arg_dict['html_report'],
        )

    elif progname.endswith('diff-quality'):
        arg_dict = parse_quality_args(sys.argv[1:])
        tool = arg_dict['violations']
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
                reporter = reporter_class(tool, input_reports)
                generate_quality_report(
                    reporter,
                    arg_dict['compare_branch'],
                    arg_dict['html_report']
                )

            # Close any reports we opened
            finally:
                for file_handle in input_reports:
                    file_handle.close()
        else:
            LOGGER.error("Quality tool not recognized: '{0}'".format(tool))
            exit(1)

if __name__ == "__main__":
    main()
