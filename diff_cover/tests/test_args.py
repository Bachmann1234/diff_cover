import contextlib
import sys
import unittest

from diff_cover.diff_cover_tool import parse_coverage_args


@contextlib.contextmanager
def nostderr():
    """
    Context manager to suppress standard error
    http://stackoverflow.com/questions/1809958/hide-stderr-output-in-unit-tests
    """
    savestderr = sys.stderr

    class Devnull:
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
        argv = ["reports/coverage.xml", "--html-report", "diff_cover.html"]

        arg_dict = parse_coverage_args(argv)

        self.assertEqual(arg_dict.get("coverage_xml"), ["reports/coverage.xml"])

        self.assertEqual(arg_dict.get("html_report"), "diff_cover.html")
        self.assertFalse(arg_dict.get("ignore_unstaged"))

    def test_parse_with_no_html_report(self):
        argv = ["reports/coverage.xml"]

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(arg_dict.get("coverage_xml"), ["reports/coverage.xml"])
        self.assertFalse(arg_dict.get("ignore_unstaged"))

    def test_parse_with_ignored_unstaged(self):
        argv = ["reports/coverage.xml", "--ignore-unstaged"]

        arg_dict = parse_coverage_args(argv)
        self.assertTrue(arg_dict.get("ignore_unstaged"))

    def test_parse_invalid_arg(self):

        # No coverage XML report specified
        invalid_argv = [[], ["--html-report", "diff_cover.html"]]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                with nostderr():
                    parse_coverage_args(argv)

    def test_parse_with_exclude(self):
        argv = ["reports/coverage.xml"]
        arg_dict = parse_coverage_args(argv)
        self.assertIsNone(arg_dict.get("exclude"))

        argv = ["reports/coverage.xml", "--exclude", "noneed/*.py"]

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(arg_dict.get("exclude"), ["noneed/*.py"])

        argv = ["reports/coverage.xml", "--exclude", "noneed/*.py", "other/**/*.py"]

        arg_dict = parse_coverage_args(argv)
        self.assertEqual(arg_dict.get("exclude"), ["noneed/*.py", "other/**/*.py"])
