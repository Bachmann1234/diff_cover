"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals
from collections import namedtuple, defaultdict
import re
import os
import six
import itertools
import posixpath

from diff_cover.command_runner import run_command_for_code
from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.base import BaseViolationReporter, BaseQualityReporter, Violation, \
    QualityReporterError


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


class Pep8QualityReporter(BaseQualityReporter):
    """
    Report PEP8 violations.
    """
    COMMAND = 'pep8'
    EXTENSIONS = ['py']
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+).*([EW]\d{3}.*)$')


class PyflakesQualityReporter(BaseQualityReporter):
    """
    Report Pyflakes violations.
    """
    COMMAND = 'pyflakes'
    EXTENSIONS = ['py']
    # Match lines of the form:
    # path/to/file.py:328: undefined name '_thing'
    # path/to/file.py:418: 'random' imported but unused
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+): (.*)$')


class Flake8QualityReporter(BaseQualityReporter):
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
    COMMAND = 'flake8'
    EXTENSIONS = ['py']
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+).*([EWFCNTIBDSQ]\d{3}.*)$')


class PylintQualityReporter(BaseQualityReporter):
    """
    Report Pylint violations.
    """
    COMMAND = 'pylint'
    MODERN_OPTIONS = ['--msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"']
    OPTIONS = MODERN_OPTIONS
    EXTENSIONS = ['py']
    DUPE_CODE_VIOLATION = 'R0801'

    # Match lines of the form:
    # path/to/file.py:123: [C0111] Missing docstring
    # path/to/file.py:456: [C0111, Foo.bar] Missing docstring
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+): \[(\w+),? ?([^\]]*)] (.*)$')
    MULTI_LINE_VIOLATION_REGEX = re.compile(r'==(\w|.+):(.*)')
    DUPE_CODE_MESSAGE_REGEX = re.compile(r'Similar lines in (\d+) files')

    def _process_dupe_code_violation(self, lines, current_line, message):
        """
        The duplicate code violation is a multi line error. This pulls out
        all the relevant files
        """
        src_paths = []
        message_match = self.DUPE_CODE_MESSAGE_REGEX.match(message)
        if message_match:
            for _ in range(int(message_match.group(1))):
                current_line += 1
                match = self.MULTI_LINE_VIOLATION_REGEX.match(
                    lines[current_line]
                )
                src_path, l_number = match.groups()
                src_paths.append(('%s.py' % src_path, l_number))
        return src_paths

    def _parse_output(self, output, src_path=None):
        """
        See base class docstring.
        """
        violations_dict = defaultdict(list)

        output_lines = output.split('\n')

        for output_line_number, line in enumerate(output_lines):
            match = self.VIOLATION_REGEX.match(line)

            # Ignore any line that isn't matched
            # (for example, snippets from the source code)
            if match is not None:

                (pylint_src_path,
                 line_number,
                 pylint_code,
                 function_name,
                 message) = match.groups()
                if pylint_code == self.DUPE_CODE_VIOLATION:
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
                    if src_path is None or src_path == pylint_src_path:

                        if function_name:
                            error_str = u"{0}: {1}: {2}".format(pylint_code, function_name, message)
                        else:
                            error_str = u"{0}: {1}".format(pylint_code, message)

                        violation = Violation(int(line_number), error_str)
                        violations_dict[pylint_src_path].append(violation)

        return violations_dict


class JsHintQualityReporter(BaseQualityReporter):
    """
    Report JSHint violations.
    """
    COMMAND = 'jshint'
    # The following command can confirm jshint is installed
    DISCOVERY_COMMAND = 'jshint -v'
    EXTENSIONS = ['js']
    VIOLATION_REGEX = re.compile(r'^([^:]+): line (\d+), col \d+, (.*)$')

    def _confirm_installed(self, name):
        """
        Override base method. Confirm the tool is installed by running this command and
        getting exit 0. Otherwise, raise an Environment Error.
        """
        if run_command_for_code(self.DISCOVERY_COMMAND) == 0:
            return
        raise EnvironmentError
