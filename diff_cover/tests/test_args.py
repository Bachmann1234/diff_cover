from diff_cover.tool import parse_coverage_args, parse_quality_args
from diff_cover.tests.helpers import unittest


class ParseArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['reports/coverage.xml',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_coverage_args(argv)

        self.assertEqual(
            arg_dict.get('coverage_xml'),
            ['reports/coverage.xml']
        )

        self.assertEqual(
            arg_dict.get('html_report'),
            'diff_cover.html'
        )

    def test_parse_with_no_html_report(self):
        argv = ['reports/coverage.xml']

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(
            arg_dict.get('coverage_xml'),
            ['reports/coverage.xml']
        )

    def test_parse_invalid_arg(self):

        # No coverage XML report specified
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_coverage_args(argv)


class ParseQualityArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['--violations', 'pep8',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_quality_args(argv)

        self.assertEqual(arg_dict.get('violations'), 'pep8')
        self.assertEqual(arg_dict.get('html_report'), 'diff_cover.html')

    def test_parse_with_no_html_report(self):
        argv = ['--violations', 'pylint']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('violations'), 'pylint')

    def test_parse_invalid_arg(self):
        # No code quality test provided
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_quality_args(argv)
