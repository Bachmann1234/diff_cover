"""
Implement the command-line tool interface.
"""

def parse_args(argv):
    """
    Parse command line arguments, returning a dict of 
    valid options:

        {
            'git-branch': BRANCH,
            'coverage-xml': COVERAGE_XML,
            'html-report': None | HTML_REPORT
        }

    """
    pass

def generate_report(arg_dict):
    """
    Given an argument dict `arg_dict` of the form returned by
    `parse_args()`, generate the appropriate diff coverage report.
    """
    pass
