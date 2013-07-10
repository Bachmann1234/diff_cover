"""
Implement the command-line tool interface.
"""
import argparse
import sys
import diff_cover
from diff_cover.diff_reporter import GitDiffReporter
from git_diff import GitDiffTool
from violations_reporter import XmlCoverageReporter, Pep8QualityReporter, PylintQualityReporter
from report_generator import HtmlReportGenerator, StringReportGenerator, HtmlQualityReportGenerator, StringQualityReportGenerator
from lxml import etree

COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"
VIOLATION_CMD_HELP = "Which code quality tool to use"

QUALITY_REPORTERS = {
    'pep8': Pep8QualityReporter,
    'pylint': PylintQualityReporter
}


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
    parser.add_argument('coverage_xml', type=str, help=COVERAGE_XML_HELP, nargs='+')
    parser.add_argument('--html-report', type=str, default=None,
                        help=HTML_REPORT_HELP)

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
    parser = argparse.ArgumentParser(description=diff_cover.QUALITY_DESCRIPTION)
    parser.add_argument('--violations', type=str, help=VIOLATION_CMD_HELP, required=True)
    parser.add_argument('--html-report', type=str, default=None,
                        help=HTML_REPORT_HELP)

    return vars(parser.parse_args(argv))


def generate_coverage_report(coverage_xml, html_report=None):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(git_diff=GitDiffTool())

    xml_roots = [etree.parse(xml_root) for xml_root in coverage_xml]
    coverage = XmlCoverageReporter(xml_roots, coverage_xml)

    # Build a report generator
    if html_report is not None:
        reporter = HtmlReportGenerator(coverage, diff)
        output_file = open(html_report, "w")
    else:
        reporter = StringReportGenerator(coverage, diff)
        output_file = sys.stdout

    # Generate the report
    reporter.generate_report(output_file)


def generate_quality_report(tool, html_report=None):
    """
    Generate the quality report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(git_diff=GitDiffTool())

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
        generate_coverage_report(arg_dict['coverage_xml'],
                                 html_report=arg_dict['html_report'])

    elif progname.endswith('diff-quality'):
        arg_dict = parse_quality_args(sys.argv[1:])
        tool = arg_dict['violations']
        reporter = QUALITY_REPORTERS[tool](tool)
        generate_quality_report(reporter, arg_dict['html_report'])


if __name__ == "__main__":
    main()
