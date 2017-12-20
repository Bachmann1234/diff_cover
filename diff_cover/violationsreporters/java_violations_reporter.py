"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals

from collections import defaultdict

import itertools
from xml.etree import cElementTree
from diff_cover.command_runner import run_command_for_code
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import BaseViolationReporter, Violation, RegexBasedDriver, QualityDriver


class CloverXmlCoverageReporter(BaseViolationReporter):
    """
    Query information from a Clover XML coverage report.
    """

    def __init__(self, xml_roots):
        """
        Load the Clover XML coverage report represented
        by the cElementTree with root element `xml_root`.
        """
        super(CloverXmlCoverageReporter, self).__init__("XML")
        self._xml_roots = xml_roots

        # Create a dict to cache violations dict results
        # Keys are source file paths, values are output of `violations()`
        self._info_cache = defaultdict(list)

    @staticmethod
    def _get_src_path_line_nodes(xml_document, src_path):
        """
        Return a list of nodes containing line information for `src_path`
        in `xml_document`.

        If file is not present in `xml_document`, return None
        """
        files = [file_tree
                 for file_tree in xml_document.findall(".//file")
                 if GitPathTool.relative_path(file_tree.get('path')) == src_path
                 or []]
        if not files:
            return None
        lines = [file_tree.findall('./line[@type="stmt"]')
                 for file_tree in files]
        return [elem for elem in itertools.chain(*lines)]

    def _cache_file(self, src_path):
        """
        Load the data from `self._xml_roots`
        for `src_path`, if it hasn't been already.
        """
        # If we have not yet loaded this source file
        if src_path not in self._info_cache:
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
                line_nodes = self._get_src_path_line_nodes(xml_document,
                                                           src_path)

                if line_nodes is None:
                    continue

                # First case, need to define violations initially
                if violations is None:
                    violations = set(
                        Violation(int(line.get('num')), None)
                        for line in line_nodes
                        if int(line.get('count', 0)) == 0)

                # If we already have a violations set,
                # take the intersection of the new
                # violations set and its old self
                else:
                    violations = violations & set(
                        Violation(int(line.get('num')), None)
                        for line in line_nodes
                        if int(line.get('count', 0)) == 0
                    )

                # Measured is the union of itself and the new measured
                measured = measured | set(
                    int(line.get('num')) for line in line_nodes
                )

            # If we don't have any information about the source file,
            # don't report any violations
            if violations is None:
                violations = set()
            self._info_cache[src_path] = (violations, measured)

    def violations(self, src_path):
        """
        See base class comments.
        """

        self._cache_file(src_path)

        # Yield all lines not covered
        return self._info_cache[src_path][0]

    def measured_lines(self, src_path):
        """
        See base class docstring.
        """
        self._cache_file(src_path)
        return self._info_cache[src_path][1]


"""
    Report checkstyle violations.

    http://checkstyle.sourceforge.net/apidocs/com/puppycrawl/tools/checkstyle/DefaultLogger.html
    https://github.com/checkstyle/checkstyle/blob/master/src/main/java/com/puppycrawl/tools/checkstyle/AuditEventDefaultFormatter.java
"""
checkstyle_driver = RegexBasedDriver(
    name='checkstyle',
    supported_extensions=['java'],
    command=['checkstyle'],
    expression=r'^\[\w+\]\s+([^:]+):(\d+):(?:\d+:)? (.*)$',
    command_to_check_install=['java', 'com.puppycrawl.tools.checkstyle.Main', '-version']
)


class CheckstyleXmlDriver(QualityDriver):
    def __init__(self):
        """
        See super for args
        """
        super(CheckstyleXmlDriver, self).__init__(
            'checkstyle',
            ['java'],
            ['java', 'com.puppycrawl.tools.checkstyle.Main', '-c',
             '/google_checks.xml']
        )
        self.command_to_check_install = ['java', 'com.puppycrawl.tools.checkstyle.Main', '-version']

    def parse_reports(self, reports):
        """
        Args:
            reports: list[str] - output from the report
        Return:
            A dict[Str:Violation]
            Violation is a simple named tuple Defined above
        """
        violations_dict = defaultdict(list)
        for report in reports:
            xml_document = cElementTree.fromstring("".join(report))
            files = xml_document.findall(".//file")
            for file_tree in files:
                for error in file_tree.findall('error'):
                    line_number = error.get('line')
                    error_str = u"{0}: {1}".format(error.get('severity'),
                                                   error.get('message'))
                    violation = Violation(int(line_number), error_str)
                    filename = GitPathTool.relative_path(file_tree.get('name'))
                    violations_dict[filename].append(violation)
        return violations_dict

    def installed(self):
        """
        Method checks if the provided tool is installed.
        Returns: boolean True if installed
        """
        return run_command_for_code(self.command_to_check_install) == 0


class FindbugsXmlDriver(QualityDriver):
    def __init__(self):
        """
        See super for args
        """
        super(FindbugsXmlDriver, self).__init__(
            'findbugs',
            ['java'],
            ['false']
        )

    def parse_reports(self, reports):
        """
        Args:
            reports: list[str] - output from the report
        Return:
            A dict[Str:Violation]
            Violation is a simple named tuple Defined above
        """
        violations_dict = defaultdict(list)
        for report in reports:
            xml_document = cElementTree.fromstring("".join(report))
            bugs = xml_document.findall(".//BugInstance")
            for bug in bugs:
                category = bug.get('category')
                short_message = bug.find('ShortMessage').text
                line = bug.find('SourceLine')
                if line.get('start') is None or line.get('end') is None:
                    continue
                start = int(line.get('start'))
                end = int(line.get('end'))
                for line_number in range(start, end+1):
                    error_str = u"{0}: {1}".format(category, short_message)
                    violation = Violation(line_number, error_str)
                    filename = GitPathTool.relative_path(
                        line.get('sourcepath'))
                    violations_dict[filename].append(violation)

        return violations_dict

    def installed(self):
        """
        Method checks if the provided tool is installed.
        Returns: boolean False: As findbugs analyses bytecode, it would be hard to run it from outside the build framework.
        """
        return False
