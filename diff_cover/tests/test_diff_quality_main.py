import unittest

from unittest.mock import patch

from diff_cover.diff_quality_tool import parse_quality_args, main


class ParseQualityArgsTest(unittest.TestCase):
    def test_parse_with_html_report(self):
        argv = ["--violations", "pycodestyle", "--html-report", "diff_cover.html"]

        arg_dict = parse_quality_args(argv)

        self.assertEqual(arg_dict.get("violations"), "pycodestyle")
        self.assertEqual(arg_dict.get("html_report"), "diff_cover.html")
        self.assertEqual(arg_dict.get("input_reports"), [])
        self.assertFalse(arg_dict.get("ignore_unstaged"))
        self.assertEqual(arg_dict.get("diff_range_notation"), "...")

    def test_parse_with_no_html_report(self):
        argv = ["--violations", "pylint"]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get("violations"), "pylint")
        self.assertEqual(arg_dict.get("input_reports"), [])
        self.assertFalse(arg_dict.get("ignore_unstaged"))
        self.assertEqual(arg_dict.get("diff_range_notation"), "...")

    def test_parse_with_one_input_report(self):
        argv = ["--violations", "pylint", "pylint_report.txt"]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get("input_reports"), ["pylint_report.txt"])

    def test_parse_with_multiple_input_reports(self):
        argv = ["--violations", "pylint", "pylint_report_1.txt", "pylint_report_2.txt"]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(
            arg_dict.get("input_reports"),
            ["pylint_report_1.txt", "pylint_report_2.txt"],
        )

    def test_parse_with_options(self):
        argv = [
            "--violations",
            "pycodestyle",
            "--options=\"--exclude='*/migrations*'\"",
        ]
        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get("options"), "\"--exclude='*/migrations*'\"")

    def test_parse_with_ignored_unstaged(self):
        argv = ["--violations", "pylint", "--ignore-unstaged"]

        arg_dict = parse_quality_args(argv)
        self.assertTrue(arg_dict.get("ignore_unstaged"))

    def test_parse_invalid_arg(self):
        # No code quality test provided
        invalid_argv = [[], ["--html-report", "diff_cover.html"]]

        for argv in invalid_argv:
            with self.assertRaises(SystemExit):
                print("args = {}".format(argv))
                parse_quality_args(argv)

    def test_parse_with_exclude(self):
        argv = ["--violations", "pep8"]
        arg_dict = parse_quality_args(argv)
        self.assertIsNone(arg_dict.get("exclude"))

        argv = ["--violations", "pep8", "--exclude", "noneed/*.py"]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get("exclude"), ["noneed/*.py"])

        argv = ["--violations", "pep8", "--exclude", "noneed/*.py", "other/**/*.py"]

        arg_dict = parse_quality_args(argv)
        self.assertEqual(arg_dict.get("exclude"), ["noneed/*.py", "other/**/*.py"])

    def test_parse_diff_range_notation(self):
        argv = ["--violations", "pep8", "--diff-range-notation=.."]

        arg_dict = parse_quality_args(argv)

        self.assertEqual(arg_dict.get("violations"), "pep8")
        self.assertIsNone(arg_dict.get("html_report"))
        self.assertEqual(arg_dict.get("input_reports"), [])
        self.assertFalse(arg_dict.get("ignore_unstaged"))
        self.assertEqual(arg_dict.get("diff_range_notation"), "..")


class MainTest(unittest.TestCase):
    """Tests for the main() function in tool.py"""

    def setUp(self):
        patch1 = patch("diff_cover.diff_quality_tool.GitPathTool")
        self.fake_GitPathTool = patch1.start()  # pylint: disable=invalid-name
        self.addCleanup(patch1.stop)

    def test_parse_options(self):
        argv = [
            "diff-quality",
            "--violations",
            "pylint",
            '--options="--foobar"',
        ]
        self._run_main(argv)

    def test_parse_options_without_quotes(self):
        argv = [
            "diff-quality",
            "--violations",
            "pylint",
            "--options=--foobar",
        ]
        self._run_main(argv)

    def _run_main(self, argv):
        gen_report_patch = patch(
            "diff_cover.diff_quality_tool.generate_quality_report", return_value=100
        )
        with gen_report_patch as p:
            main(argv)
            quality_reporter = p.call_args[0][0]
            assert quality_reporter.driver.name == "pylint"
            assert quality_reporter.options == "--foobar"
