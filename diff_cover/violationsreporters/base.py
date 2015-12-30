from __future__ import unicode_literals, absolute_import
from abc import ABCMeta, abstractmethod
from collections import defaultdict, namedtuple

import subprocess

import sys

import six

from diff_cover.command_runner import execute

Violation = namedtuple('Violation', 'line, message')


class QualityReporterError(Exception):
    """
    A quality reporter command produced an error.
    """
    pass


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
        Retrieve the name of the report, which may be
        included in the generated diff coverage report.

        For example, `name()` could return the path to the coverage
        report file or the type of reporter.
        """
        return self._name


class BaseQualityReporter(BaseViolationReporter):
    """
    Abstract class to report code quality
    information, using `COMMAND`
    (provided by subclasses).
    """
    COMMAND = ''
    DISCOVERY_COMMAND = ''
    OPTIONS = []

    # A list of filetypes to run on.
    EXTENSIONS = []

    def __init__(self, name, input_reports, user_options=None):
        """
        Create a new quality reporter.

        `name` is an identifier for the reporter
        (usually the name of the tool used to generate
        the report).

        `input_reports` is an list of
        file-like objects representing pre-generated
        violation reports.  The list can be empty.

        If these are provided, the reporter will
        use the pre-generated reports instead of invoking
        the tool directly.

        'user_options' is a string of options passed in.
        This string contains options that are passed forward
        to the reporter being used

        This raises an ImportError if the tool being created
        is not installed.
        """
        super(BaseQualityReporter, self).__init__(name)
        # Test if the tool requested is installed
        self._confirm_installed(name)
        self._info_cache = defaultdict(list)
        self.user_options = user_options

        # If we've been given input report files, use those
        # to get the source information
        if len(input_reports) > 0:
            self.use_tool = False
            self._load_reports(input_reports)
        else:
            self.use_tool = True

    def violations(self, src_path):
        """
        See base class comments.
        """
        # If we've been given pre-generated pylint/pep8 reports,
        # then we've already loaded everything we need into the cache.
        # Otherwise, call pylint/pep8 ourselves
        if self.use_tool:
            if not any(src_path.endswith(ext) for ext in self.EXTENSIONS):
                return []
            if src_path not in self._info_cache:
                user_options = [self.user_options] if self.user_options else []
                command = [self.COMMAND] + self.OPTIONS + user_options + [src_path.encode(sys.getfilesystemencoding())]
                output, _ = execute(command)
                violations_dict = self._parse_output(output, src_path)
                self._update_cache(violations_dict)

        # Return the cached violation info
        return self._info_cache[src_path]

    def _load_reports(self, report_files):
        """
        Load pre-generated pep8/pylint reports into
        the cache.

        `report_files` is a list of open file-like objects.
        """
        for file_handle in report_files:
            # Convert to unicode, replacing unreadable chars
            contents = file_handle.read().decode('utf-8',
                                                 'replace')
            violations_dict = self._parse_output(contents)
            self._update_cache(violations_dict)

    def _update_cache(self, violations_dict):
        """
        Append violations in `violations_dict` to the cache.
        `violations_dict` must have the form:

            {
                SRC_PATH: [Violation, ]
            }
        """
        for src_path, violations in six.iteritems(violations_dict):
            self._info_cache[src_path].extend(violations)

    def _confirm_installed(self, name):
        """
        Assumes it can be imported with the same name.
        This applies to all python tools so far
        """
        __import__(name)

    def _parse_output(self, output, src_path=None):
        """
        Parse the output of this reporter
        command into a dict of the form:

            {
                SRC_PATH: [Violation, ]
            }

        where `SRC_PATH` is the path to the source file
        containing the violations, and the value is
        a list of violations.

        If `src_path` is provided, return information
        just for that source.
        """
        violations_dict = defaultdict(list)

        for line in output.split('\n'):

            match = self.VIOLATION_REGEX.match(line)

            # Ignore any line that isn't a violation
            if match is not None:
                src, line_number, message = match.groups()

                # If we're looking for a particular source,
                # filter out all other sources
                if src_path is None or src_path == src:
                    violation = Violation(int(line_number), message)
                    violations_dict[src].append(violation)

        return violations_dict