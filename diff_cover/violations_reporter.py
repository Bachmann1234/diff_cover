"""
Classes for querying the information in a test coverage report.
"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple, defaultdict
import re
import subprocess


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
        Return a list of the lines in src_path that were measured
        by this reporter.

        Some reporters will always consider all lines in the file "measured".
        As an optimization, such violation reporters
        can return `None` to indicate that all lines are measured.
        The diff reporter generator will then use all changed lines
        provided by the diff.
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
        Load the data from `self._xml_roots`
        for `src_path`, if it hasn't been already.
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

                # Check that we've actually found a source file
                src_element = xml_document.find(".//class[@filename='{0}']".format(src_path))
                if src_element is not None:
                    line_nodes = xml_document.findall(xpath)

                    # First case, need to define violations initially
                    if violations is None:
                        violations = set(
                            Violation(int(line.get('number')), None)
                            for line in line_nodes
                            if int(line.get('hits', 0)) == 0)

                    # If we already have a violations set,
                    # take the intersection of the new
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


class BaseQualityReporter(BaseViolationReporter):
    """
    Abstract class to report code quality
    information, using `COMMAND`
    (provided by subclasses).
    """
    COMMAND = ''
    OPTIONS = []

    # A list of filetypes to run on.
    EXTENSIONS = []

    def __init__(self, name, input_reports):
        """
        Create a new quality reporter.

        `name` is an identifier for the reporter
        (usually the name of the tool used to generate
        the report).

        `input_reports` is an optional list of
        paths to pre-generated violation reports.
        If this is provided, the reporter will
        use the pre-generated reports instead of invoking
        the tool directly.
        """
        super(BaseQualityReporter, self).__init__(name)
        self._info_cache = defaultdict(list)

    def violations(self, src_path):
        """
        See base class comments.
        """
        if not any(src_path.endswith(ext) for ext in self.EXTENSIONS):
            return []
        if src_path not in self._info_cache:
            output = self._run_command(src_path)
            violations = [
                Violation(*violation)
                for violation in self._parse_output(output, src_path)
            ]
            self._info_cache[src_path] = violations

        return self._info_cache[src_path]

    def _run_command(self, src_path):
        """
        Run the quality command and return its output.
        """
        command = '{0} {1} {2}'.format(self.COMMAND, self.OPTIONS, src_path)
        command = [self.COMMAND] + self.OPTIONS + [src_path]

        # DEBUG
        print str(command)

        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if stderr:
            raise QualityReporterError(stderr)

        return stdout.strip()

    @abstractmethod
    def _parse_output(self, output, src_path):
        """
        Parse the output of this reporter
        command into a list of (line, violation) pairs.

        Return only violations for the source at `src_path`.
        """
        pass


class Pep8QualityReporter(BaseQualityReporter):
    """
    Report PEP8 violations.
    """
    COMMAND = 'pep8'

    EXTENSIONS = ['py']

    def _parse_output(self, output, src_path):
        lines = output.split('\n')
        regex = re.compile(r'^.*\.py:(\d+).*([EW]\d{3}.*$)')
        violations = []
        for line in lines:
            # Sometimes pep8 gives us a blank line
            if line == '':
                continue
            line_number, message = regex.match(line).groups()
            violations.append((int(line_number), message))
        return violations


class PylintQualityReporter(BaseQualityReporter):
    """
    Report Pylint violations.
    """
    COMMAND = 'pylint'
    OPTIONS = ['-f', 'parseable', '--reports=no', '--include-ids=y']

    EXTENSIONS = ['py']

    # Match lines of the form:
    # path/to/file.py:123: [C0111] Missing docstring 
    # path/to/file.py:456: [C0111, Foo.bar] Missing docstring
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+): \[(\w+),? ?([^\]]*)] (.*)$')

    def _parse_output(self, output, src_path):
        lines = output.split('\n')
        violations = []

        for line in lines:
            match = self.VIOLATION_REGEX.match(line)

            # Ignore any line that isn't matched
            # (for example, snippets from the source code)
            if match is not None:

                pylint_src_path, line_number, pylint_code, function_name, message = match.groups()

                # Add the violation only if it's for the source file
                # we're looking for.
                if src_path == pylint_src_path:

                    if function_name:
                        error_str = "{0}: {1}: {2}".format(pylint_code, function_name, message)
                    else:
                        error_str = "{0}: {1}".format(pylint_code, message)

                    violation_tuple = (int(line_number), error_str)
                    violations.append(violation_tuple)

        return violations


class QualityReporterError(Exception):
    """
    A quality reporter command produced an error.
    """
    pass
