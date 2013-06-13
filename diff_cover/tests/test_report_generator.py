import unittest
import mock
import StringIO
from textwrap import dedent
from diff_cover.diff_reporter import BaseDiffReporter
from diff_cover.coverage_reporter import BaseCoverageReporter
from diff_cover.report_generator import BaseReportGenerator, \
        HtmlReportGenerator, StringReportGenerator


class SimpleReportGenerator(BaseReportGenerator):
    """
    Bare-bones concrete implementation of a report generator.
    """

    def __init__(self, cover, diff):
        super(SimpleReportGenerator, self).__init__(cover, diff)

    def generate_report(self, output_file):
        pass


class BaseReportGeneratorTest(unittest.TestCase):
    """
    Base class for constructing test cases of report generators.
    """

    # Test data, returned by default from the mocks
    SRC_PATHS = ['file1.py', 'subdir/file2.py']
    LINES = [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]
    COVERAGE = {1: True, 2: True, 3: True,
                4: True, 7: True, 10: False, 11: False, 15: True,
                20: False, 30: True}
    XML_REPORT_NAME = "reports/coverage.xml"
    DIFF_REPORT_NAME = "master"

    # Subclasses override this to provide the class under test
    REPORT_GENERATOR_CLASS = None

    def setUp(self):

        # Create mocks of the dependencies
        self.coverage = mock.MagicMock(BaseCoverageReporter)
        self.diff = mock.MagicMock(BaseDiffReporter)

        # Set the names of the XML and diff reports
        self.coverage.name.return_value = self.XML_REPORT_NAME
        self.diff.name.return_value = self.DIFF_REPORT_NAME

        # Have the mocks return default values
        self.set_src_paths_changed(self.SRC_PATHS)
        self.set_lines_changed(self.LINES)
        self.set_coverage_info(self.COVERAGE)

        # Create a concrete instance of a report generator
        self.report = self.REPORT_GENERATOR_CLASS(self.coverage, self.diff)

    def set_src_paths_changed(self, src_paths):
        """
        Patch the dependency `src_paths_changed()` return value
        """
        self.diff.src_paths_changed.return_value = src_paths

    def set_lines_changed(self, lines):
        """
        Patch the dependency `lines_changed()` return value
        """
        self.diff.lines_changed.return_value = lines

    def set_coverage_info(self, coverage_info):
        """
        Patch the dependency `coverage_info()` return value
        """
        self.coverage.coverage_info.return_value = coverage_info


class SimpleReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = SimpleReportGenerator

    def test_src_paths(self):
        self.assertEqual(self.report.src_paths(), self.SRC_PATHS)

    def test_coverage_name(self):
        self.assertEqual(self.report.coverage_report_name(),
                         self.XML_REPORT_NAME)

    def test_diff_name(self):
        self.assertEqual(self.report.diff_report_name(),
                         self.DIFF_REPORT_NAME)

    def test_percent_covered(self):

        # Check that we get the expected coverage percentages
        # By construction, both files have the same diff line
        # and coverage information
        # Because the diff_reporter is reponsible for
        # filtering non-diff lines, we expect to get
        # all the lines included
        for src_path in self.SRC_PATHS:
            self.assertEqual(self.report.percent_covered(src_path), 70)

    def test_missing_lines(self):

        # By construction, each file has the same coverage information
        expected = [10, 11, 20]
        for src_path in self.SRC_PATHS:
            self.assertEqual(self.report.missing_lines(src_path), expected)

    def test_src_with_no_info(self):

        self.assertIs(self.report.percent_covered('unknown.py'), None)
        self.assertEqual(self.report.missing_lines('unknown.py'), [])

    def test_total_num_lines(self):

        # By construction, each source file has the same coverage info
        expected = len(self.SRC_PATHS) * len(self.COVERAGE)
        self.assertEqual(self.report.total_num_lines(), expected)

    def test_total_num_missing(self):

        # By construction, each source file has the same coverage info,
        # in which 3 lines are uncovered
        expected = len(self.SRC_PATHS) * 3
        self.assertEqual(self.report.total_num_missing(), expected)

    def test_total_percent_covered(self):

        # Since each file has the same coverage info,
        # the total percent covered is the same as each file
        # individually.
        self.assertEqual(self.report.total_percent_covered(), 70)


class StringReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = StringReportGenerator

    def test_generate_report(self):

        # Create a buffer for the output
        output = StringIO.StringIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue().strip()
        output.close()

        # Verify that we got the expected string
        expected = dedent("""
        -------------
        Diff Coverage
        Coverage Report: reports/coverage.xml
        Diff: master
        -------------
        file1.py (70%): Missing line(s) 10,11,20
        subdir/file2.py (70%): Missing line(s) 10,11,20
        -------------
        Total:   20 line(s)
        Missing: 6 line(s)
        Coverage: 70%
        -------------
        """).strip()

        self.assertEqual(output_str, expected)

    def test_hundred_percent(self):

        # Create a buffer for the output
        output = StringIO.StringIO()

        # Have the dependencies return an empty report
        self.set_src_paths_changed(['file.py'])
        self.set_lines_changed([line for line in range(0, 100)])
        self.set_coverage_info({2: True})

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue().strip()
        output.close()

        # Verify that we got the expected string
        expected = dedent("""
        -------------
        Diff Coverage
        Coverage Report: reports/coverage.xml
        Diff: master
        -------------
        file.py (100%)
        -------------
        Total:   1 line(s)
        Missing: 0 line(s)
        Coverage: 100%
        -------------
        """).strip()

        self.assertEqual(output_str, expected)

    def test_empty_report(self):

        # Have the dependencies return an empty report
        self.set_src_paths_changed([])
        self.set_lines_changed([])
        self.set_coverage_info(dict())

        # Create a buffer for the output
        output = StringIO.StringIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue().strip()
        output.close()

        # Verify that we got the expected string
        expected = dedent("""
        -------------
        Diff Coverage
        Coverage Report: reports/coverage.xml
        Diff: master
        -------------
        No lines with coverage information in this diff.
        -------------
        """).strip()

        self.assertEqual(output_str, expected)


class HtmlReportGeneratorTest(BaseReportGeneratorTest):

    REPORT_GENERATOR_CLASS = HtmlReportGenerator

    def test_generate_report(self):

        # Create a buffer for the output
        output = StringIO.StringIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue()
        output.close()

        # Verify that we got the expected string
        expected = dedent("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
        <head>
        <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
        <title>Diff Coverage</title>
        </head>
        <body>
        <h1>Diff Coverage</h1>
        <p>Coverage Report: reports/coverage.xml</p>
        <p>Diff: master</p>
        <table border="1">
        <tr>
        <th>Source File</th>
        <th>Diff Coverage (%)</th>
        <th>Missing Line(s)</th>
        </tr>
        <tr>
        <td>file1.py</td>
        <td>70%</td>
        <td>10,11,20</td>
        </tr>
        <tr>
        <td>subdir/file2.py</td>
        <td>70%</td>
        <td>10,11,20</td>
        </tr>
        </table>
        <ul>
        <li><b>Total</b>: 20 line(s)</li>
        <li><b>Missing</b>: 6 line(s)</li>
        <li><b>Coverage</b>: 70%</li>
        </ul>
        </body>
        </html>
        """).strip()

        self.assertEqual(output_str, expected)

    def test_empty_report(self):

        # Have the dependencies return an empty report
        self.set_src_paths_changed([])
        self.set_lines_changed([])
        self.set_coverage_info(dict())

        # Create a buffer for the output
        output = StringIO.StringIO()

        # Generate the report
        self.report.generate_report(output)

        # Get the output
        output_str = output.getvalue()
        output.close()

        # Verify that we got the expected string
        expected = dedent("""
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
        <html>
        <head>
        <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
        <title>Diff Coverage</title>
        </head>
        <body>
        <h1>Diff Coverage</h1>
        <p>Coverage Report: reports/coverage.xml</p>
        <p>Diff: master</p>
        <p>No lines with coverage information in this diff.</p>
        </body>
        </html>
        """).strip()

        self.assertEqual(output_str, expected)
