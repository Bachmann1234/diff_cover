"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals

import re
from collections import defaultdict

import os
import itertools
import posixpath
from diff_cover.command_runner import run_command_for_code
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import BaseViolationReporter, Violation, RegexBasedDriver, QualityDriver


class XmlCoverageReporter(BaseViolationReporter):
    """
    Query information from a Cobertura XML coverage report.
    """

    def __init__(self, xml_roots):
        """
        Load the Cobertura XML coverage report represented
        by the cElementTree with root element `xml_root`.
        """
        super(XmlCoverageReporter, self).__init__("XML")
        self._xml_roots = xml_roots

        # Create a dict to cache violations dict results
        # Keys are source file paths, values are output of `violations()`
        self._info_cache = defaultdict(list)

    @staticmethod
    def _to_unix_path(path):
        """
        Tries to ensure tha the path is a normalized unix path.
        This seems to be the solution cobertura used....
        https://github.com/cobertura/cobertura/blob/642a46eb17e14f51272c6962e64e56e0960918af/cobertura/src/main/java/net/sourceforge/cobertura/instrument/ClassPattern.java#L84

        I know of at least one case where this will fail (\\) is allowed in unix paths.
        But I am taking the bet that this is not common. We deal with source code.

        :param path: string of the path to convert
        :return: the unix version of that path
        """
        return posixpath.normpath(path.replace("\\", '/'))

    def _get_classes(self, xml_document, src_path):
        """
        Given a path and parsed xml_document provides class nodes
        with the relevant lines

        First, we look to see if xml_document contains a source
        node providing paths to search for

        If we don't have that we check each nodes filename attribute
        matches an absolute path

        Finally, if we found no nodes, we check the filename attribute
        for the relative path
        """
        # Remove git_root from src_path for searching the correct filename
        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `diff_cover/violations_reporter.py`
        # search for `violations_reporter.py`
        src_rel_path = self._to_unix_path(GitPathTool.relative_path(src_path))

        # If cwd is `/home/user/work/diff-cover/diff_cover`
        # and src_path is `other_package/some_file.py`
        # search for `/home/user/work/diff-cover/other_package/some_file.py`
        src_abs_path = self._to_unix_path(GitPathTool.absolute_path(src_path))

        # cobertura sometimes provides the sources for the measurements
        # within it. If we have that we outta use it
        sources = xml_document.findall('sources/source')
        sources = [source.text for source in sources]
        classes = [class_tree
                   for class_tree in xml_document.findall(".//class")
                   or []]

        classes = (
            [clazz for clazz in classes if
             src_abs_path in [
                 self._to_unix_path(
                     os.path.join(
                         source,
                         clazz.get('filename')
                     )
                 ) for source in sources]]
            or
            [clazz for clazz in classes if
             self._to_unix_path(clazz.get('filename')) == src_abs_path]
            or
            [clazz for clazz in classes if
             self._to_unix_path(clazz.get('filename')) == src_rel_path]
        )
        return classes

    def _get_src_path_line_nodes(self, xml_document, src_path):
        """
        Returns a list of nodes containing line information for `src_path`
        in `xml_document`.

        If file is not present in `xml_document`, return None
        """

        classes = self._get_classes(xml_document, src_path)

        if not classes:
            return None
        else:
            lines = [clazz.findall('./lines/line') for clazz in classes]
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

pep8_driver = RegexBasedDriver(
    name='pep8',
    supported_extensions=['py'],
    command=['pep8'],
    expression=r'^([^:]+):(\d+).*([EW]\d{3}.*)$',
    command_to_check_install=['pep8', '--version']
)

pyflakes_driver = RegexBasedDriver(
    name='pyflakes',
    supported_extensions=['py'],
    command=['pyflakes'],
    # Match lines of the form:
    # path/to/file.py:328: undefined name '_thing'
    # path/to/file.py:418: 'random' imported but unused
    expression=r'^([^:]+):(\d+): (.*)$',
    command_to_check_install=['pyflakes', '--version']
)

"""
    Report Flake8 violations.

    Flake8 warning/error codes:
        E***/W***: pep8 errors and warnings
        F***: pyflakes codes
        C9**: mccabe complexity plugin
        N8**: pep8-naming plugin
        T000: flake8-todo plugin

    http://flake8.readthedocs.org/en/latest/warnings.html
"""
flake8_driver = RegexBasedDriver(
    name='flake8',
    supported_extensions=['py'],
    command=['flake8'],
    # Match lines of the form:
    # path/to/file.py:328: undefined name '_thing'
    # path/to/file.py:418: 'random' imported but unused
    expression=r'^([^:]+):(\d+).*([EWFCNTIBDSQ]\d{3}.*)$',
    command_to_check_install=['flake8', '--version']
)

jshint_driver = RegexBasedDriver(
    name='jshint',
    supported_extensions=['js'],
    command=['jshint'],
    expression=r'^([^:]+): line (\d+), col \d+, (.*)$',
    command_to_check_install=['jshint', '-v']
)

eslint_driver = RegexBasedDriver(
    name='eslint',
    supported_extensions=['js'],
    command=['eslint', '--format=compact'],
    expression=r'^([^:]+): line (\d+), col \d+, (.*)$',
    command_to_check_install=['eslint', '-v'],
)


class PylintDriver(QualityDriver):
    def __init__(self):
        """
        args:
            expression: regex used to parse report
        See super for other args
        """
        super(PylintDriver, self).__init__(
                'pylint',
                ['py'],
                ['pylint', '--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"']
        )
        self.pylint_expression = re.compile(r'^([^:]+):(\d+): \[(\w+),? ?([^\]]*)] (.*)$')
        self.dupe_code_violation = 'R0801'
        self.command_to_check_install = ['pylint', '--version']

        # Match lines of the form:
        # path/to/file.py:123: [C0111] Missing docstring
        # path/to/file.py:456: [C0111, Foo.bar] Missing docstring
        self.multi_line_violation_regex = re.compile(r'==(\w|.+):(.*)')
        self.dupe_code_violation_regex = re.compile(r'Similar lines in (\d+) files')

    def _process_dupe_code_violation(self, lines, current_line, message):
        """
        The duplicate code violation is a multi line error. This pulls out
        all the relevant files
        """
        src_paths = []
        message_match = self.dupe_code_violation_regex.match(message)
        if message_match:
            for _ in range(int(message_match.group(1))):
                current_line += 1
                match = self.multi_line_violation_regex.match(
                    lines[current_line]
                )
                src_path, l_number = match.groups()
                src_paths.append(('%s.py' % src_path, l_number))
        return src_paths

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
            output_lines = report.split('\n')

            for output_line_number, line in enumerate(output_lines):
                match = self.pylint_expression.match(line)

                # Ignore any line that isn't matched
                # (for example, snippets from the source code)
                if match is not None:

                    (pylint_src_path,
                     line_number,
                     pylint_code,
                     function_name,
                     message) = match.groups()
                    if pylint_code == self.dupe_code_violation:
                        files_involved = self._process_dupe_code_violation(
                            output_lines,
                            output_line_number,
                            message
                        )
                    else:
                        files_involved = [(pylint_src_path, line_number)]

                    for violation in files_involved:
                        pylint_src_path, line_number = violation
                        # If we're looking for a particular source file,
                        # ignore any other source files.
                        if function_name:
                            error_str = u"{0}: {1}: {2}".format(pylint_code, function_name, message)
                        else:
                            error_str = u"{0}: {1}".format(pylint_code, message)

                        violation = Violation(int(line_number), error_str)
                        violations_dict[pylint_src_path].append(violation)

        return violations_dict

    def installed(self):
        """
        Method checks if the provided tool is installed.
        Returns: boolean True if installed
        """
        return run_command_for_code(self.command_to_check_install) == 0
