"""
Classes for querying the information in a test coverage report.
"""

from abc import ABCMeta, abstractmethod

class BaseCoverageReporter(object):
    """
    Query information from a coverage report.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def coverage_info(self, src_path, line_start, line_end):
        """
        For each line in `src_path` between `line_start` and `line_end`
        (inclusive), indicate whether the line is covered or uncovered
        by the test suite.

        Returns a dict with line number keys and True/False values.
        For example:

            { 5: True, 6: False}

        indicates that line 5 is covered, but line 6 is uncovered in the
        source file.
        """
        pass

class XmlCoverageReporter(BaseCoverageReporter):
    """
    Query information from a Cobertura XML coverage report.
    """

    def __init__(self, xml_root):
        """
        Load the Cobertura XML coverage report represented
        by the lxml.etree with root element `xml_root`.
        """
        super(XmlCoverageReporter, self).__init__()

    def coverage_info(self, src_path, line_start, line_end):
        pass
