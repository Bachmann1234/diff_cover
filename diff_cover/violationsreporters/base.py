from __future__ import unicode_literals, absolute_import
from abc import ABCMeta, abstractmethod
from collections import defaultdict, namedtuple


import copy

import re
import sys
import os


from diff_cover.command_runner import execute, run_command_for_code

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


class QualityDriver(object):
    __metaclass__ = ABCMeta

    def __init__(self, name, supported_extensions, command, exit_codes=[0]):
        """
        Args:
            name: (str) name of the driver
            supported_extensions: (list[str]) list of file extensions this driver supports
                Example: py, js
            command: (list[str]) list of tokens that are the command to be executed
                to create a report
        """
        self.name = name
        self.supported_extensions = supported_extensions
        self.command = command
        self.exit_codes = exit_codes

    @abstractmethod
    def parse_reports(self, reports):
        """
        Args:
            reports: list[str] - output from the report
        Return:
            A dict[Str:Violation]
            Violation is a simple named tuple Defined above
        """
        pass

    @abstractmethod
    def installed(self):
        """
        Method checks if the provided tool is installed.
        Returns: boolean True if installed
        """
        pass


class QualityReporter(BaseViolationReporter):

    def __init__(self, driver, reports=None, options=None):
        """
        Args:
            driver (QualityDriver) object that works with the underlying quality tool
            reports (list[file]) pre-generated reports. If not provided the tool will be run instead.
            options (str) options to be passed into the command
        """
        super(QualityReporter, self).__init__(driver.name)
        self.reports = self._load_reports(reports) if reports else None
        self.violations_dict = defaultdict(list)
        self.driver = driver
        self.options = options
        self.driver_tool_installed = None

    def _load_reports(self, report_files):
        """
        Args:
            report_files: list[file] reports to read in
        """
        contents = []
        for file_handle in report_files:
            # Convert to unicode, replacing unreadable chars
            contents.append(
                file_handle.read().decode(
                    'utf-8',
                    'replace'
                )
            )
        return contents

    def violations(self, src_path):
        """
        Return a list of Violations recorded in `src_path`.
        """
        if not any(src_path.endswith(ext) for ext in self.driver.supported_extensions):
            return []
        if src_path not in self.violations_dict:
            if self.reports:
                self.violations_dict = self.driver.parse_reports(self.reports)
            else:
                if self.driver_tool_installed is None:
                    self.driver_tool_installed = self.driver.installed()
                if not self.driver_tool_installed:
                    raise EnvironmentError("{} is not installed".format(self.driver.name))
                command = copy.deepcopy(self.driver.command)
                if self.options:
                    command.append(self.options)
                if os.path.exists(src_path):
                    command.append(src_path.encode(sys.getfilesystemencoding()))
                    output, _ = execute(command, self.driver.exit_codes)
                    self.violations_dict.update(self.driver.parse_reports([output]))

        return self.violations_dict[src_path]

    def measured_lines(self, src_path):
        """
        Quality Reports Consider all lines measured
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


class RegexBasedDriver(QualityDriver):
    def __init__(
            self,
            name,
            supported_extensions,
            command,
            expression,
            command_to_check_install,
            flags=0,
            exit_codes=[0]
    ):
        """
        args:
            expression: regex used to parse report, will be fed lines singly
                        unless flags contain re.MULTILINE
            flags: such as re.MULTILINE
        See super for other args
            command_to_check_install: (list[str]) command to run
            to see if the tool is installed
        """
        super(RegexBasedDriver, self).__init__(name, supported_extensions, command, exit_codes)
        self.expression = re.compile(expression, flags)
        self.command_to_check_install = command_to_check_install
        self.is_installed = None

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
            if self.expression.flags & re.MULTILINE:
                matches = (match for match in
                           re.finditer(self.expression, report))
            else:
                matches = (self.expression.match(line) for line in
                           report.split('\n'))
            for match in matches:
                if match is not None:
                    src, line_number, message = match.groups()
                    # Transform src to a relative path, if it isn't already
                    src = os.path.relpath(src)
                    violation = Violation(int(line_number), message)
                    violations_dict[src].append(violation)
        return violations_dict

    def installed(self):
        """
        Method checks if the provided tool is installed.
        Returns: boolean True if installed
        """
        return run_command_for_code(self.command_to_check_install) == 0
