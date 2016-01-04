from __future__ import unicode_literals
import contextlib
import sys
from mock import Mock, patch
from diff_cover.tool import parse_coverage_args, parse_quality_args, main
from diff_cover.tests.helpers import unittest


@contextlib.contextmanager
def nostderr():
    """
    Context manager to suppress standard error
    http://stackoverflow.com/questions/1809958/hide-stderr-output-in-unit-tests
    """
    savestderr = sys.stderr

    class Devnull(object):
        """
        Mock class to suppress stderr
        """
        def write(self, _):
            pass
    sys.stderr = Devnull()
    try:
        yield
    finally:
        sys.stderr = savestderr


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
        self.assertEqual(arg_dict.get('ignore_unstaged'), False)

    def test_parse_with_no_html_report(self):
        argv = ['reports/coverage.xml']

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(
            arg_dict.get('coverage_xml'),
            ['reports/coverage.xml']
        )
        self.assertEqual(arg_dict.get('ignore_unstaged'), False)

    def test_parse_with_ignored_unstaged(self):
        argv = ['reports/coverage.xml', '--ignore-unstaged']

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(arg_dict.get('ignore_unstaged'), True)

    def test_parse_invalid_arg(self):

        # No coverage XML report specified
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                with nostderr():
                    parse_coverage_args(argv)


class ParseQualityArgsTest(unittest.TestCase):

    def test_parse_with_html_report(self):
        argv = ['--violations', 'pep8',
                '--html-report', 'diff_cover.html']

        arg_dict = parse_quality_args(argv)

        self.assertEqual(arg_dict.get('violations'), 'pep8')
        self.assertEqual(arg_dict.get('html_report'), 'diff_cover.html')
        self.assertEqual(arg_dict.get('input_reports'), [])
        self.assertEqual(arg_dict.get('ignore_unstaged'), False)

    def test_parse_with_no_html_report(self):
        argv = ['--violations', 'pylint']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('violations'), 'pylint')
        self.assertEqual(arg_dict.get('input_reports'), [])
        self.assertEqual(arg_dict.get('ignore_unstaged'), False)

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

    def test_parse_with_options(self):
        argv = [
            '--violations', 'pep8',
            '--options="--exclude=\'*/migrations*\'"'
        ]
        arg_dict = parse_quality_args(argv)
        self.assertEqual(
            arg_dict.get('options'),
            '"--exclude=\'*/migrations*\'"'
        )

    def test_parse_with_ignored_unstaged(self):
        argv = ['--violations', 'pylint', '--ignore-unstaged']

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get('ignore_unstaged'), True)

    def test_parse_invalid_arg(self):
        # No code quality test provided
        invalid_argv = [[], ['--html-report', 'diff_cover.html']]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {0}".format(argv))
                parse_quality_args(argv)


class MainTest(unittest.TestCase):
    """Tests for the main() function in tool.py"""

    def setUp(self):
        patch1 = patch("diff_cover.tool.GitPathTool")
        self.fake_GitPathTool = patch1.start()  # pylint: disable=invalid-name
        self.addCleanup(patch1.stop)

    def test_parse_options(self):
        argv = [
            "diff-quality",
            "--violations", "pylint",
            '--options="--foobar"',
        ]
        self._run_main(argv)

    def test_parse_options_without_quotes(self):
        argv = [
            "diff-quality",
            "--violations", "pylint",
            '--options=--foobar',
        ]
        self._run_main(argv)

    def test_parse_prog_name(self):
        # Windows will give the full path to the tool.
        argv = [
            # Using forward slashes so the tests work everywhere.
            'C:/diff-cover/diff-quality-script.py',
            '--violations', 'pylint',
            '--options=--foobar',
        ]
        self._run_main(argv)

        # No silent failures if the tool name is unrecognized.
        with self.assertRaises(AssertionError):
            main(['diff-foobar'])

    def _run_main(self, argv):
        gen_report_patch = patch("diff_cover.tool.generate_quality_report",
                                 return_value=100)
        with gen_report_patch as p:
            main(argv)
            quality_reporter = p.call_args[0][0]
            assert quality_reporter.driver.name == 'pylint'
            assert quality_reporter.options == '--foobar'
