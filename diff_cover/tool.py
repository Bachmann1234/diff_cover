"""
Implement the command-line tool interface.
"""
import argparse
import sys
import diff_cover
from diff_reporter import GitDiffReporter
from git_diff import GitDiffTool
from violations_reporter import XmlCoverageReporter
from report_generator import HtmlReportGenerator, StringReportGenerator
from lxml import etree

COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"


def parse_args(argv):
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


def generate_report(coverage_xml=None, html_report=None):
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


def main():
    """
    Main entry point for the tool, used by setup.py
    """
    arg_dict = parse_args(sys.argv[1:])
    generate_report(coverage_xml=arg_dict['coverage_xml'],
                    html_report=arg_dict['html_report'])

if __name__ == "__main__":
    main()
