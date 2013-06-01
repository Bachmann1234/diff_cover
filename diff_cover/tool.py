"""
Implement the command-line tool interface.
"""
import argparse
import sys
from diff_reporter import GitDiffReporter
from coverage_reporter import XmlCoverageReporter
from report_generator import HtmlReportGenerator, StringReportGenerator
from lxml import etree

DESCRIPTION = "Automatically find diff lines that need test coverage."
GIT_BRANCH_HELP = "Git branch to compare against the current branch."
COVERAGE_XML_HELP = "XML coverage report"
HTML_REPORT_HELP = "Diff coverage HTML output"


def parse_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'git_branch': BRANCH,
            'coverage_xml': COVERAGE_XML,
            'html_report': None | HTML_REPORT
        }

    where `BRANCH` is the (string) name of the git branch to compare,
    `COVERAGE_XML` is a path, and `HTML_REPORT` is a path.

    The path strings may or may not exist.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('coverage_xml', type=str, help=COVERAGE_XML_HELP)
    parser.add_argument('--git-branch', type=str, default='master',
                        help=GIT_BRANCH_HELP)
    parser.add_argument('--html-report', type=str, default=None,
                        help=HTML_REPORT_HELP)

    return vars(parser.parse_args(argv))


def generate_report(coverage_xml=None, git_branch=None, html_report=None):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(git_branch)
    xml_root = etree.parse(coverage_xml)
    coverage = XmlCoverageReporter(xml_root)

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
                    git_branch=arg_dict['git_branch'],
                    html_report=arg_dict['html_report'])

if __name__ == "__main__":
    main()
