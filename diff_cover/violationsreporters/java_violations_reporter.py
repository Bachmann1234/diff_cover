"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals

from collections import defaultdict

from xml.etree import cElementTree
from diff_cover.command_runner import run_command_for_code
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import BaseViolationReporter, Violation, RegexBasedDriver, QualityDriver


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
                    error_str = "{}: {}".format(error.get('severity'),
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
                    error_str = "{}: {}".format(category, short_message)
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
