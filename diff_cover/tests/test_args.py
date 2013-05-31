import unittest
from diff_cover.tool import parse_args, generate_report

class ParseArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['reports/coverage.xml', '--git-branch', 'master',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('git_branch'), 'master')
        self.assertEqual(arg_dict.get('coverage_xml'), 'reports/coverage.xml')
        self.assertEqual(arg_dict.get('html_report'), 'diff_cover.html')

    def test_parse_with_no_html_report(self):
        argv = ['reports/coverage.xml', '--git-branch', 'master']

        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('git_branch'), 'master')
        self.assertEqual(arg_dict.get('coverage_xml'), 'reports/coverage.xml')

    def test_default_git_branch(self):
        argv = ['reports/coverage.xml']

        arg_dict = parse_args(argv)

        self.assertEqual(arg_dict.get('git_branch'), 'master')
        self.assertEqual(arg_dict.get('coverage_xml'), 'reports/coverage.xml')

    def test_parse_invalid_arg(self):

        # No coverage XML report specified
        invalid_argv = [[], ['--html-report', 'diff_cover.html'],
                        ['--git-branch', 'master']] # No report file specified

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_args(argv)
