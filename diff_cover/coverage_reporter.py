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
        self._xml = xml_root

        # Create a dict to cache coverage_info dict results
        # Keys are source file paths, values are output of `coverage_info()`
        self._info_cache = dict()

    def coverage_info(self, src_path, line_start, line_end):
        """
        See base class comments.
        """

        # If we have not yet loaded this source file
        if src_path not in self._info_cache:

            # Retrieve the <line> elements for this file
            xpath = ".//class[@filename='{0}']/lines/line".format(src_path)
            line_nodes = self._xml.findall(xpath)

            # If nothing found, then no coverage information
            if len(line_nodes) < 1:
                self._info_cache[src_path] = dict()

            # Process each line element
            else:
                results_dict = dict()

                for line in line_nodes:

                    line_num = int(line.get('number'))
                    line_hits = int(line.get('hits'))
                    results_dict[line_num] = (line_hits > 0)

                # Store the result in the cache
                self._info_cache[src_path] = results_dict

        # Return the line numbers that match the range
        src_line_dict = self._info_cache[src_path]

        return {key: src_line_dict[key] for key in src_line_dict.keys()
                 if key >= line_start and key <= line_end}
