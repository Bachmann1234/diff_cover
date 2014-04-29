from __future__ import unicode_literals
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
        self.assertEqual(arg_dict.get('input_reports'), [])

    def test_parse_with_no_html_report(self):
        argv = ['--violations', 'pylint']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('violations'), 'pylint')
        self.assertEqual(arg_dict.get('input_reports'), [])

    def test_parse_with_one_input_report(self):
        argv = ['--violations', 'pylint', 'pylint_report.txt']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('input_reports'), ['pylint_report.txt'])

    def test_parse_with_multiple_input_reports(self):
        argv = [
            '--violations', 'pylint',
            'pylint_report_1.txt', 'pylint_report_2.txt'
        ]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(
            arg_dict.get('input_reports'),
            ['pylint_report_1.txt', 'pylint_report_2.txt']
        )

    def test_parse_invalid_arg(self):
        # No code quality test provided
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_quality_args(argv)
