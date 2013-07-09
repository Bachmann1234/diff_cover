import unittest
from lxml import etree
from diff_cover.violations_reporter import XmlCoverageReporter, Violation


class XmlCoverageReporterTest(unittest.TestCase):

    MANY_VIOLATIONS = set([Violation(3, None), Violation(7, None), Violation(11, None), Violation(13, None)])
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
        self.assertEqual(measured, coverage.measured('file1.py'))

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
        self.assertEqual(violations1 & violations2, coverage.violations('file1.py'))
        self.assertEqual(measured1 | measured2, coverage.measured('file1.py'))

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
        self.assertEqual(violations1 & violations2, coverage.violations('file1.py'))
        self.assertEqual(measured1 | measured2, coverage.measured('file1.py'))

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
        self.assertEqual(violations1 & violations2 & violations3, coverage.violations('file1.py'))
        self.assertEqual(measured1 | measured2 | measured3, coverage.measured('file1.py'))

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
        self.assertEqual(violations1 & violations2, coverage.violations('file1.py'))
        self.assertEqual(measured1 | measured2, coverage.measured('file1.py'))

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
