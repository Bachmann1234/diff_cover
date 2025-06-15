# pylint: disable=attribute-defined-outside-init,not-callable

import copy
import json
from io import BytesIO
from textwrap import dedent

import pytest

from diff_cover.diff_reporter import BaseDiffReporter
from diff_cover.report_generator import (
    BaseReportGenerator,
    HtmlReportGenerator,
    JsonReportGenerator,
    MarkdownReportGenerator,
    StringReportGenerator,
    TemplateReportGenerator,
)
from diff_cover.violationsreporters.violations_reporter import (
    BaseViolationReporter,
    Violation,
)
from tests.helpers import load_fixture


class SimpleReportGenerator(BaseReportGenerator):
    """Bare-bones concrete implementation of a report generator."""

    def generate_report(self, output_file):
        pass


class BaseReportGeneratorTest:
    """Base class for constructing test cases of report generators."""

    # Test data, returned by default from the mocks
    SRC_PATHS = {"file1.py", "subdir/file2.py"}
    LINES = [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]
    VIOLATIONS = [Violation(n, None) for n in (10, 11, 20)]
    MEASURED = [1, 2, 3, 4, 7, 10, 11, 15, 20, 30]

    @pytest.fixture
    def coverage_violations(self):
        return {}

    @pytest.fixture
    def coverage_measured_lines(self):
        return {}

    @pytest.fixture
    def coverage(self, mocker, coverage_violations, coverage_measured_lines):
        coverage = mocker.MagicMock(BaseViolationReporter)
        coverage.name.return_value = ["reports/coverage.xml"]
        coverage.violations.side_effect = coverage_violations.get
        coverage.violations_batch.side_effect = NotImplementedError
        coverage.measured_lines.side_effect = coverage_measured_lines.get
        return coverage

    @pytest.fixture
    def diff_lines_changed(self):
        return {}

    @pytest.fixture
    def diff(self, mocker, diff_lines_changed):
        diff = mocker.MagicMock(BaseDiffReporter)
        diff.name.return_value = "main"
        diff.lines_changed.side_effect = diff_lines_changed.get
        diff.src_paths_changed.return_value = []
        return diff

    @pytest.fixture(autouse=True)
    def base_setup(self, mocker, report, diff):
        # Create mocks of the dependencies

        # Patch snippet loading to always return the same string
        self._load_formatted_snippets = mocker.patch(
            "diff_cover.snippets.Snippet.load_formatted_snippets"
        )

        self.set_num_snippets(0)

        # Patch snippet style
        style_defs = mocker.patch("diff_cover.snippets.Snippet.style_defs")

        style_defs.return_value = ".css { color:red }"

        # Set the names of the XML and diff reports

        # Configure the mocks
        self.diff = diff
        self.report = report

    def set_num_snippets(self, num_snippets):
        """
        Patch the depdenency `Snippet.load_snippets_html()`
        to return `num_snippets` of the fake snippet HTML.
        """
        self._load_formatted_snippets.return_value = {
            "html": num_snippets * ["<div>Snippet with \u1235 \u8292 unicode</div>"],
            "markdown": num_snippets
            * ["Lines 1-1\n\n```\nSnippet with \u1235 \u8292 unicode\n```"],
            "terminal": num_snippets
            * ["Lines 1-1\n\n```\nSnippet with \u1235 \u8292 unicode\n```"],
        }

    @pytest.fixture
    def use_default_values(
        self, diff, diff_lines_changed, coverage_violations, coverage_measured_lines
    ):
        """
        Configure the mocks to use default values
        provided by class constants.

        All source files are given the same line, violation,
        and measured information.
        """
        diff.src_paths_changed.return_value = self.SRC_PATHS

        for src in self.SRC_PATHS:
            diff_lines_changed.update({src: self.LINES})
            coverage_violations.update({src: self.VIOLATIONS})
            coverage_measured_lines.update({src: self.MEASURED})
        self.set_num_snippets(0)

    def get_report(self):
        """
        Generate a report and assert that it matches
        the string `expected`.
        """
        # Create a buffer for the output
        output = BytesIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue()
        output.close()

        return output_str.decode("utf-8")

    def assert_report(self, expected):
        output_report_string = self.get_report()
        assert expected.strip() == output_report_string.strip()


class TestSimpleReportGenerator(BaseReportGeneratorTest):
    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return SimpleReportGenerator(coverage, diff)

    @pytest.fixture(autouse=True)
    def setup(self, use_default_values):
        del use_default_values

    def test_src_paths(self):
        assert self.report.src_paths() == self.SRC_PATHS

    def test_coverage_name(self):
        assert self.report.coverage_report_name() == ["reports/coverage.xml"]

    def test_diff_name(self):
        assert self.report.diff_report_name() == "main"

    def test_percent_covered(self):
        # Check that we get the expected coverage percentages
        # By construction, both files have the same diff line
        # and coverage information

        # There are 6 lines that are both in the diff and measured,
        # and 4 of those are covered.
        for src_path in self.SRC_PATHS:
            assert self.report.percent_covered(src_path) == pytest.approx(4.0 / 6 * 100)

    def test_violation_lines(self):
        # By construction, each file has the same coverage information
        expected = [10, 11]
        for src_path in self.SRC_PATHS:
            assert self.report.violation_lines(src_path) == expected

    def test_src_with_no_info(self):
        assert "unknown.py" not in self.report.src_paths()
        assert self.report.percent_covered("unknown.py") is None
        assert self.report.violation_lines("unknown.py") == []

    def test_src_paths_not_measured(self, coverage_measured_lines, coverage_violations):
        # Configure one of the source files to have no coverage info
        coverage_measured_lines.update({"file1.py": []})
        coverage_violations.update({"file1.py": []})

        # Expect that we treat the file like it doesn't exist
        assert "file1.py" not in self.report.src_paths()
        assert self.report.percent_covered("file1.py") is None
        assert self.report.violation_lines("file1.py") == []

    def test_total_num_lines(self):
        # By construction, each source file has the same coverage info
        num_lines_in_file = len(set(self.MEASURED).intersection(self.LINES))
        expected = len(self.SRC_PATHS) * num_lines_in_file
        assert self.report.total_num_lines() == expected

    def test_total_num_missing(self):
        # By construction, each source file has the same coverage info,
        # in which 3 lines are uncovered, 2 of which are changed
        expected = len(self.SRC_PATHS) * 2
        assert self.report.total_num_violations() == expected

    def test_total_percent_covered(self):
        # Since each file has the same coverage info,
        # the total percent covered is the same as each file
        # individually.
        assert self.report.total_percent_covered() == 66


class TestTemplateReportGenerator(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return TemplateReportGenerator(coverage, diff)

    def _test_input_expected_output(self, input_with_expected_output):
        for test_input, expected_output in input_with_expected_output:
            assert expected_output == TemplateReportGenerator.combine_adjacent_lines(
                test_input
            )

    def test_combine_adjacent_lines_no_adjacent(self):
        in_out = [([1, 3], ["1", "3"]), ([1, 5, 7, 10], ["1", "5", "7", "10"])]
        self._test_input_expected_output(in_out)

    def test_combine_adjacent_lines(self):
        in_out = [
            ([1, 2, 3, 4, 5, 8, 10, 12, 13, 14, 15], ["1-5", "8", "10", "12-15"]),
            ([1, 4, 5, 6, 10], ["1", "4-6", "10"]),
            ([402, 403], ["402-403"]),
        ]
        self._test_input_expected_output(in_out)

    def test_empty_list(self):
        assert TemplateReportGenerator.combine_adjacent_lines([]) == []

    def test_one_number(self):
        assert TemplateReportGenerator.combine_adjacent_lines([1]) == ["1"]


class TestJsonReportGenerator(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return JsonReportGenerator(coverage, diff)

    def assert_report(self, expected):
        output_report_string = self.get_report()
        assert json.loads(expected) == json.loads(output_report_string)

    @pytest.mark.usefixtures("use_default_values")
    def test_generate_report(self):
        # Verify that we got the expected string
        expected = json.dumps(
            {
                "report_name": ["reports/coverage.xml"],
                "diff_name": "main",
                "src_stats": {
                    "file1.py": {
                        "covered_lines": [2, 3, 4, 15],
                        "percent_covered": 66.66666666666667,
                        "violation_lines": [10, 11],
                        "violations": [[10, None], [11, None]],
                    },
                    "subdir/file2.py": {
                        "covered_lines": [2, 3, 4, 15],
                        "percent_covered": 66.66666666666667,
                        "violation_lines": [10, 11],
                        "violations": [[10, None], [11, None]],
                    },
                },
                "total_num_lines": 12,
                "total_num_violations": 4,
                "total_percent_covered": 66,
                "num_changed_lines": len(self.SRC_PATHS) * len(self.LINES),
            }
        )

        self.assert_report(expected)

    def test_hundred_percent(
        self, diff, diff_lines_changed, coverage_violations, coverage_measured_lines
    ):
        # Have the dependencies return an empty report
        diff.src_paths_changed.return_value = ["file.py"]
        diff_lines_changed.update({"file.py": list(range(100))})
        coverage_violations.update({"file.py": []})
        coverage_measured_lines.update({"file.py": [2]})

        expected = json.dumps(
            {
                "report_name": ["reports/coverage.xml"],
                "diff_name": "main",
                "src_stats": {
                    "file.py": {
                        "covered_lines": [2],
                        "percent_covered": 100.0,
                        "violation_lines": [],
                        "violations": [],
                    }
                },
                "total_num_lines": 1,
                "total_num_violations": 0,
                "total_percent_covered": 100,
                "num_changed_lines": 100,
            }
        )

        self.assert_report(expected)

    def test_empty_report(self):
        # Have the dependencies return an empty report
        # (this is the default)

        expected = json.dumps(
            {
                "report_name": ["reports/coverage.xml"],
                "diff_name": "main",
                "src_stats": {},
                "total_num_lines": 0,
                "total_num_violations": 0,
                "total_percent_covered": 100,
                "num_changed_lines": 0,
            }
        )

        self.assert_report(expected)


class TestStringReportGenerator(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return StringReportGenerator(coverage, diff)

    @pytest.mark.usefixtures("use_default_values")
    def test_generate_report(self):
        # Verify that we got the expected string
        expected = dedent(
            """
        -------------
        Diff Coverage
        Diff: main
        -------------
        file1.py (66.7%): Missing lines 10-11
        subdir/file2.py (66.7%): Missing lines 10-11
        -------------
        Total:   12 lines
        Missing: 4 lines
        Coverage: 66%
        -------------
        """
        ).strip()

        self.assert_report(expected)

    def test_hundred_percent(
        self, diff, diff_lines_changed, coverage_violations, coverage_measured_lines
    ):
        # Have the dependencies return an empty report
        diff.src_paths_changed.return_value = ["file.py"]
        diff_lines_changed.update({"file.py": list(range(100))})
        coverage_violations.update({"file.py": []})
        coverage_measured_lines.update({"file.py": [2]})

        expected = dedent(
            """
        -------------
        Diff Coverage
        Diff: main
        -------------
        file.py (100%)
        -------------
        Total:   1 line
        Missing: 0 lines
        Coverage: 100%
        -------------
        """
        ).strip()

        self.assert_report(expected)

    def test_empty_report(self):
        # Have the dependencies return an empty report
        # (this is the default)

        expected = dedent(
            """
        -------------
        Diff Coverage
        Diff: main
        -------------
        No lines with coverage information in this diff.
        -------------
        """
        ).strip()

        self.assert_report(expected)


class TestHtmlReportGenerator(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return HtmlReportGenerator(coverage, diff)

    @pytest.mark.usefixtures("use_default_values")
    def test_generate_report(self):
        expected = load_fixture("html_report.html")
        self.assert_report(expected)

    def test_empty_report(self):
        # Have the dependencies return an empty report
        # (this is the default)

        # Verify that we got the expected string
        expected = load_fixture("html_report_empty.html")
        self.assert_report(expected)

    @pytest.mark.usefixtures("use_default_values")
    def test_one_snippet(self):
        # Have the snippet loader always report
        # provide one snippet (for every source file)
        self.set_num_snippets(1)

        # Verify that we got the expected string
        expected = load_fixture("html_report_one_snippet.html").strip()
        self.assert_report(expected)

    @pytest.mark.usefixtures("use_default_values")
    def test_multiple_snippets(self):
        # Have the snippet loader always report
        # multiple snippets for each source file
        self.set_num_snippets(2)

        # Verify that we got the expected string
        expected = load_fixture("html_report_two_snippets.html").strip()
        self.assert_report(expected)


class TestMarkdownReportGenerator(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return MarkdownReportGenerator(coverage, diff)

    @pytest.mark.usefixtures("use_default_values")
    def test_generate_report(self):
        # Generate a default report

        # Verify that we got the expected string
        expected = dedent(
            """
        # Diff Coverage
        ## Diff: main

        - file1&#46;py (66.7%): Missing lines 10-11
        - subdir/file2&#46;py (66.7%): Missing lines 10-11

        ## Summary

        - **Total**: 12 lines
        - **Missing**: 4 lines
        - **Coverage**: 66%
        """
        ).strip()

        self.assert_report(expected)

    def test_hundred_percent(
        self, diff, diff_lines_changed, coverage_violations, coverage_measured_lines
    ):
        # Have the dependencies return an empty report
        diff.src_paths_changed.return_value = ["file.py"]
        diff_lines_changed.update({"file.py": list(range(100))})
        coverage_violations.update({"file.py": []})
        coverage_measured_lines.update({"file.py": [2]})

        expected = dedent(
            """
        # Diff Coverage
        ## Diff: main

        - file&#46;py (100%)

        ## Summary

        - **Total**: 1 line
        - **Missing**: 0 lines
        - **Coverage**: 100%
        """
        ).strip()

        self.assert_report(expected)

    def test_empty_report(self):
        # Have the dependencies return an empty report
        # (this is the default)

        expected = dedent(
            """
        # Diff Coverage
        ## Diff: main

        No lines with coverage information in this diff.
        """
        ).strip()

        self.assert_report(expected)

    @pytest.mark.usefixtures("use_default_values")
    def test_one_snippet(self):
        # Have the snippet loader always report
        # provide one snippet (for every source file)
        self.set_num_snippets(1)

        # Verify that we got the expected string
        expected = load_fixture("markdown_report_one_snippet.md").strip()
        self.assert_report(expected)

    @pytest.mark.usefixtures("use_default_values")
    def test_multiple_snippets(self):
        # Have the snippet loader always report
        # multiple snippets for each source file
        self.set_num_snippets(2)

        # Verify that we got the expected string
        expected = load_fixture("markdown_report_two_snippets.md").strip()
        self.assert_report(expected)


class TestSimpleReportGeneratorWithBatchViolationReporter(BaseReportGeneratorTest):

    @pytest.fixture
    def report(self, coverage, diff):
        # Create a concrete instance of a report generator
        return SimpleReportGenerator(coverage, diff)

    @pytest.fixture(autouse=True)
    def setup(self, use_default_values, coverage, coverage_violations):
        del use_default_values
        # Have violations_batch() return the violations.
        coverage.violations_batch.side_effect = None
        coverage.violations_batch.return_value = coverage_violations
        # Have violations() return an empty list to ensure violations_batch()
        # is used.
        for src in self.SRC_PATHS:
            coverage_violations.update({src: []})

    def test_violation_lines(self):
        # By construction, each file has the same coverage information
        expected = []
        for src_path in self.SRC_PATHS:
            assert self.report.violation_lines(src_path) == expected
