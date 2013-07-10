"""
Classes for querying the information in a test coverage report.
"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple, defaultdict


Violation = namedtuple('Violation', 'line, message')


class BaseViolationReporter(object):
    """
    Query information from a coverage report.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name):
        """
        Provide a name for the coverage report, which will be included
        in the generated diff report.
        """
        self._name = name

    @abstractmethod
    def violations(self, src_path):
        """
        Return a list of Violations recorded in `src_path`.
        """
        pass

    def measured_lines(self, src_path):
        """
        Return a list of the lines in src_path that were measured by this reporter,
        or None if all lines were measured
        """
        return None

    def name(self):
        """
        Retrieve the name of the report, to be included in the generated
        diff report.

        For example, `name()` could return the path to the coverage
        report file.
        """
        return self._name


class XmlCoverageReporter(BaseViolationReporter):
    """
    Query information from a Cobertura XML coverage report.
    """

    def __init__(self, xml_roots, name):
        """
        Load the Cobertura XML coverage report represented
        by the lxml.etree with root element `xml_root`.

        `name` is a name used to identify the report, which will
        be included in the generated diff coverage report.
        """
        super(XmlCoverageReporter, self).__init__(name)
        self._xml_roots = xml_roots

        # Create a dict to cache violations dict results
        # Keys are source file paths, values are output of `violations()`
        self._info_cache = defaultdict(list)

    def _cache_file(self, src_path):
        """
        Load the data from `self._xml_roots` for `src_path`, if it hasn't been already
        """
        # If we have not yet loaded this source file
        if src_path not in self._info_cache:

            # Retrieve the <line> elements for this file
            xpath = ".//class[@filename='{0}']/lines/line".format(src_path)

            # We only want to keep violations that show up in each xml source.
            # Thus, each time, we take the intersection.  However, to do this
            # we must treat the first time as a special case and just add all
            # the violations from the first xml report.
            violations = None

            # A line is measured if it is measured in any of the reports, so
            # we take set union each time and can just start with the empty set
            measured = set()

            # Loop through the files that contain the xml roots
            for xml_document in self._xml_roots:
                line_nodes = xml_document.findall(xpath)

                # First case, need to define violations initially
                if violations is None:
                    violations = set(
                        Violation(int(line.get('number')), None)
                        for line in line_nodes
                        if int(line.get('hits', 0)) == 0)

                # If we already have a violations set, take the intersection of the new
                # violations set and its old self
                else:
                    violations = violations & set(
                        Violation(int(line.get('number')), None)
                        for line in line_nodes
                        if int(line.get('hits', 0)) == 0
                    )

                # Measured is the union of itself and the new measured
                measured = measured | set(
                    int(line.get('number')) for line in line_nodes
                )

            self._info_cache[src_path] = (violations, measured)

    def violations(self, src_path):
        """
        See base class comments.
        """

        self._cache_file(src_path)

        # Yield all lines not covered
        return self._info_cache[src_path][0]

    def measured(self, src_path):
        """
        See base class docstring
        """
        self._cache_file(src_path)
        return self._info_cache[src_path][1]
