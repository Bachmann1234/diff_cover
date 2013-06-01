import unittest
from lxml import etree
from diff_cover.coverage_reporter import XmlCoverageReporter


class XmlCoverageReporterTest(unittest.TestCase):

    def test_coverage_info(self):

        # Construct the XML report
        file_paths = ['file1.py', 'subdir/file2.py']
        line_dict = {2: True, 3: False, 5: True, 6: False, 8: False}
        xml = self._coverage_xml(file_paths, line_dict)

        # Parse the report
        coverage = XmlCoverageReporter(xml)

        # By construction, each file has the same set
        # of covered/uncovered lines
        result = coverage.coverage_info('file1.py', 1, 8)
        self.assertEqual(result, line_dict)

        # Try getting a smaller range
        result = coverage.coverage_info('subdir/file2.py', 3, 7)
        expected = {3: False, 5: True, 6: False}
        self.assertEqual(result, expected)

        # Once more on the first file (for caching)
        result = coverage.coverage_info('file1.py', 5, 7)
        expected = {5: True, 6: False}
        self.assertEqual(result, expected)

    def test_no_such_file(self):

        # Construct the XML report with no source files
        xml = self._coverage_xml([], dict())

        # Parse the report
        coverage = XmlCoverageReporter(xml)

        # Expect that we get no results
        result = coverage.coverage_info('file.py', 1, 100)
        self.assertEqual(result, dict())

    def test_no_such_line(self):
        # Construct the XML report
        file_paths = ['file.py']
        line_dict = {2: True, 3: False, 5: True, 6: False, 8: False}
        xml = self._coverage_xml(file_paths, line_dict)

        # Parse the report
        coverage = XmlCoverageReporter(xml)

        result = coverage.coverage_info('file.py', 10, 15)
        self.assertEqual(result, dict())

    def _coverage_xml(self, file_paths, line_dict):
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

        for path in file_paths:

            src_node = etree.SubElement(classes, 'class')
            src_node.set('filename', path)

            etree.SubElement(src_node, 'methods')
            lines_node = etree.SubElement(src_node, 'lines')

            # Create a node for each line
            for (line_num, is_covered) in line_dict.items():
                line = etree.SubElement(lines_node, 'line')

                hits = 1 if is_covered else 0
                line.set('hits', str(hits))
                line.set('number', str(line_num))

        return root
