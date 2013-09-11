from lxml import etree
from mock import patch
from subprocess import Popen
from textwrap import dedent
from diff_cover.violations_reporter import XmlCoverageReporter, Violation, \
    Pep8QualityReporter, PylintQualityReporter, QualityReporterError
from diff_cover.tests.helpers import unittest


class XmlCoverageReporterTest(unittest.TestCase):

    MANY_VIOLATIONS = set([Violation(3, None), Violation(7, None),
                           Violation(11, None), Violation(13, None)])
    FEW_MEASURED = set([2, 3, 5, 7, 11, 13])

    FEW_VIOLATIONS = set([Violation(3, None), Violation(11, None)])
    MANY_MEASURED = set([2, 3, 5, 7, 11, 13, 17])

    ONE_VIOLATION = set([Violation(11, None)])
    VERY_MANY_MEASURED = set([2, 3, 5, 7, 11, 13, 17, 23, 24, 25, 26, 26, 27])

    def test_violations(self):

        # Construct the XML report
        name = "subdir/coverage.xml"
        file_paths = ['file1.py', 'subdir/file2.py']
        violations = self.MANY_VIOLATIONS
        measured = self.FEW_MEASURED
        xml = self._coverage_xml(file_paths, violations, measured)

        # Parse the report
        coverage = XmlCoverageReporter(xml, name)

        # Expect that the name is set
        self.assertEqual(coverage.name(), name)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(violations, coverage.violations('file1.py'))
        self.assertEqual(measured, coverage.measured_lines('file1.py'))

        # Try getting a smaller range
        result = coverage.violations('subdir/file2.py')
        self.assertEqual(result, violations)

        # Once more on the first file (for caching)
        result = coverage.violations('file1.py')
        self.assertEqual(result, violations)

    def test_two_inputs_first_violate(self):

        # Construct the XML report
        name = "subdir/coverage.xml"
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml, xml2], name)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_two_inputs_second_violate(self):

        # Construct the XML report
        name = "subdir/coverage.xml"
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml], name)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_three_inputs(self):

        # Construct the XML report
        name = "subdir/coverage.xml"
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = self.FEW_VIOLATIONS
        violations3 = self.ONE_VIOLATION

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED
        measured3 = self.VERY_MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)
        xml3 = self._coverage_xml(file_paths, violations3, measured3)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml, xml3], name)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2 & violations3,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2 | measured3,
            coverage.measured_lines('file1.py')
        )

    def test_different_files_in_inputs(self):

        # Construct the XML report
        xml_roots = [
            self._coverage_xml(['file.py'], self.MANY_VIOLATIONS, self.FEW_MEASURED),
            self._coverage_xml(['other_file.py'], self.FEW_VIOLATIONS, self.MANY_MEASURED)
        ]

        # Parse the report
        coverage = XmlCoverageReporter(xml_roots, 'coverage.xml')

        self.assertEqual(self.MANY_VIOLATIONS, coverage.violations('file.py'))
        self.assertEqual(self.FEW_VIOLATIONS, coverage.violations('other_file.py'))

    def test_empty_violations(self):
        """
        Test that an empty violations report is handled properly
        """

        # Construct the XML report
        name = "subdir/coverage.xml"
        file_paths = ['file1.py']

        violations1 = self.MANY_VIOLATIONS
        violations2 = set()

        measured1 = self.FEW_MEASURED
        measured2 = self.MANY_MEASURED

        xml = self._coverage_xml(file_paths, violations1, measured1)
        xml2 = self._coverage_xml(file_paths, violations2, measured2)

        # Parse the report
        coverage = XmlCoverageReporter([xml2, xml], name)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(
            violations1 & violations2,
            coverage.violations('file1.py')
        )

        self.assertEqual(
            measured1 | measured2,
            coverage.measured_lines('file1.py')
        )

    def test_no_such_file(self):

        # Construct the XML report with no source files
        xml = self._coverage_xml([], [], [])

        # Parse the report
        coverage = XmlCoverageReporter(xml, '')

        # Expect that we get no results
        result = coverage.violations('file.py')
        self.assertEqual(result, set([]))

    def _coverage_xml(self, file_paths, violations, measured):
        """
        Build an XML tree with source files specified by `file_paths`.
        Each source fill will have the same set of covered and
        uncovered lines.

        `file_paths` is a list of path strings
        `line_dict` is a dictionary with keys that are line numbers
        and values that are True/False indicating whether the line
        is covered

        This leaves out some attributes of the Cobertura format,
        but includes all the elements.
        """
        root = etree.Element('coverage')
        packages = etree.SubElement(root, 'packages')
        classes = etree.SubElement(packages, 'classes')

        violation_lines = set(violation.line for violation in violations)

        for path in file_paths:

            src_node = etree.SubElement(classes, 'class')
            src_node.set('filename', path)

            etree.SubElement(src_node, 'methods')
            lines_node = etree.SubElement(src_node, 'lines')

            # Create a node for each line in measured
            for line_num in measured:
                is_covered = line_num not in violation_lines
                line = etree.SubElement(lines_node, 'line')

                hits = 1 if is_covered else 0
                line.set('hits', str(hits))
                line.set('number', str(line_num))

        return root


class Pep8QualityReporterTest(unittest.TestCase):

    def tearDown(self):
        """
        Undo all patches
        """
        patch.stopall()

    def test_quality(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = (
            '\n' + dedent("""
                ../new_file.py:1:17: E231 whitespace
                ../new_file.py:3:13: E225 whitespace
                ../new_file.py:7:1: E302 blank lines
            """).strip() + '\n', ''
        )

        violations = [
            Violation(1, 'E231 whitespace'),
            Violation(3, 'E225 whitespace'),
            Violation(7, 'E302 blank lines')
        ]
        name = "pep8"

        # Parse the report
        quality = Pep8QualityReporter(name)

        # Expect that the name is set
        self.assertEqual(quality.name(), name)

        # Measured_lines is undefined for
        # a quality reporter since all lines are measured
        self.assertEqual(quality.measured_lines('file1.py'), None)

        # By construction, each file has the same set
        # of covered/uncovered lines
        self.assertEqual(violations, quality.violations('file1.py'))

    def test_no_quality_issues_newline(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ('\n', '')
        violations = []
        name = "pep8"

        # Parse the report
        quality = Pep8QualityReporter(name)
        self.assertEqual(violations, quality.violations('file1.py'))

    def test_no_quality_issues_emptystring(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ('', '')
        violations = []
        name = "pep8"

        # Parse the report
        quality = Pep8QualityReporter(name)
        self.assertEqual(violations, quality.violations('file1.py'))

    def test_quality_error(self):

        # Patch the output of `pep8`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ("", 'whoops')

        name = "pep8"

        # Parse the report
        quality = Pep8QualityReporter(name)

        # Expect that the name is set
        self.assertEqual(quality.name(), name)

        self.assertRaises(QualityReporterError, quality.violations, 'file1.py')

    def test_no_such_file(self):
        quality = Pep8QualityReporter('pep8')

        # Expect that we get no results
        result = quality.violations('')
        self.assertEqual(result, [])

    def test_no_python_file(self):
        quality = Pep8QualityReporter('pep8')
        file_paths = ['file1.coffee', 'subdir/file2.js']
        # Expect that we get no results because no Python files
        for path in file_paths:
            result = quality.violations(path)
            self.assertEqual(result, [])


class PylintQualityReporterTest(unittest.TestCase):

    def tearDown(self):
        """
        Undo all patches.
        """
        patch.stopall()

    def test_no_such_file(self):
        quality = PylintQualityReporter('pylint')

        # Expect that we get no results
        result = quality.violations('')
        self.assertEqual(result, [])

    def test_no_python_file(self):
        quality = PylintQualityReporter('pylint')
        file_paths = ['file1.coffee', 'subdir/file2.js']
        # Expect that we get no results because no Python files
        for path in file_paths:
            result = quality.violations(path)
            self.assertEqual(result, [])

    def test_quality(self):
        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()

        _mock_communicate.return_value = (
            dedent("""
            ************* Module new_file
            C0111:  1,0: Missing docstring
            def func_1(apple,my_list):
                            ^^
            C0111:  1,0:func_1: Missing docstring

            W0612:  2,4:func_1: Unused variable 'd'
            W0511: 2,10: TODO: Not the real way we'll store usages!
            """).strip(), ''
        )

        violations = [
            Violation(1, 'C0111: Missing docstring'),
            Violation(1, 'C0111: func_1: Missing docstring'),
            Violation(2, "W0612: func_1: Unused variable 'd'"),
            Violation(2, "W0511: TODO: Not the real way we'll store usages!")
        ]
        name = "pylint"

        # Parse the report
        quality = PylintQualityReporter(name)

        # Expect that the name is set
        self.assertEqual(quality.name(), name)

        # Measured_lines is undefined for a
        # quality reporter since all lines are measured
        self.assertEqual(quality.measured_lines('file1.py'), None)

        # By construction, each file has the same set
        # of covered/uncovered lines
        lines = quality.violations('file1.py')
        print len(lines)
        print lines

        self.assertEqual(violations, quality.violations('file1.py'))

    def test_quality_error(self):

        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ("", 'whoops')

        name = "pylint"

        # Parse the report
        quality = PylintQualityReporter(name)

        # Expect that the name is set
        self.assertEqual(quality.name(), name)

        self.assertRaises(QualityReporterError, quality.violations, 'file1.py')

    def test_no_quality_issues_newline(self):

        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ('\n', '')
        violations = []
        name = "pylint"

        # Parse the report
        quality = PylintQualityReporter(name)
        self.assertEqual(violations, quality.violations('file1.py'))

    def test_no_quality_issues_emptystring(self):

        # Patch the output of `pylint`
        _mock_communicate = patch.object(Popen, 'communicate').start()
        _mock_communicate.return_value = ('', '')
        violations = []
        name = "pylint"

        # Parse the report
        quality = PylintQualityReporter(name)
        self.assertEqual(violations, quality.violations('file1.py'))
