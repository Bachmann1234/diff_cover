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

class SimpleReportGeneratorTest(unittest.TestCase):

    SRC_PATHS = ['file1.py', 'subdir/file2.py']
    HUNKS = [(2, 5), (10, 15)]
    COVERAGE = { 1: True, 2: True, 3: True, 
                 4: True, 7: True, 10: False, 11: False, 15: True, 
                 20: False, 30: True}

    def setUp(self):

        # Create mocks of the dependencies
        self.coverage = mock.MagicMock(BaseCoverageReporter)
        self.diff = mock.MagicMock(BaseDiffReporter)

        # Have the mocks return required values
        self.diff.src_paths_changed.return_value = self.SRC_PATHS
        self.diff.hunks_changed.return_value = self.HUNKS
        self.coverage.coverage_info.return_value = self.COVERAGE

        # Create a concrete instance of a report generator
        self.report = SimpleReportGenerator(self.coverage, self.diff)

    def test_diff_coverage(self):

        # Generate diff coverage based on mock inputs
        result = self.report.diff_coverage()

        # Check that we get the expected coverage dict
        # By construction, both files have the same hunk
        # and coverage information
        # Because the diff_reporter is reponsible for 
        # filtering non-diff lines, we expect to get
        # all the lines included
        expected_files = { 'file1.py': self.COVERAGE,
                           'subdir/file2.py': self.COVERAGE }

        self.assertEqual(result, expected_files)

class StringReportGeneratorTest(unittest.TestCase):

    def setUp(self):

        # Create a report generator
        self.report = StringReportGenerator(None, None)

        # Mock the superclass `diff_coverage()` method
        # (this is the only access the subclass has to 
        # the dependencies).
        cover_dict = { 'file1.py': { 2: True, 5: True, 6: False, 
                                     7: False, 24: True },
                       'subdir/file2.py': { 3: False, 10: True },
                       'subdir/file3.py': { 4: True }}

        self.report.diff_coverage = mock.Mock(return_value=cover_dict)

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
        Diff Coverage
        -------------
        file1.py (60%): Missing line(s) 6,7
        subdir/file2.py (50%): Missing line(s) 3
        subdir/file3.py (100%)
        """).strip()

        self.assertEqual(output_str, expected)

class HtmlReportGeneratorTest(unittest.TestCase):

    def setUp(self):

        # Create a report generator
        self.report = HtmlReportGenerator(None, None)

        # Mock the superclass `diff_coverage()` method
        # (this is the only access the subclass has to 
        # the dependencies).
        cover_dict = { 'file1.py': { 2: True, 5: True, 6: False, 
                                     7: False, 24: True },
                       'subdir/file2.py': { 3: False, 10: True },
                       'subdir/file3.py': { 4: True }}

        self.report.diff_coverage = mock.Mock(return_value=cover_dict)

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
        <table border="1">
        <tr>
        <th>Source File</th>
        <th>Diff Coverage (%)</th>
        <th>Missing Line(s)</th>
        </tr>
        <tr>
        <td>file1.py</td>
        <td>60%</td>
        <td>6,7</td>
        </tr>
        <tr>
        <td>subdir/file2.py</td>
        <td>50%</td>
        <td>3</td>
        </tr>
        <tr>
        <td>subdir/file3.py</td>
        <td>100%</td>
        <td>&nbsp;</td>
        </tr>
        </table>
        </body>
        </html>
        """).strip()

        self.assertEqual(output_str, expected)
