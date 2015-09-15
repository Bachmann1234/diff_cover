"""
Classes for querying the information in a test coverage report.
"""
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod
from collections import namedtuple, defaultdict
import re
import subprocess
import sys
import os
import six
import itertools
import posixpath
from diff_cover.git_path import GitPathTool


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
        Retrieve the name of the report, which may be
        included in the generated diff coverage report.

        For example, `name()` could return the path to the coverage
        report file or the type of reporter.
        """
        return self._name


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


class BaseQualityReporter(BaseViolationReporter):
    """
    Abstract class to report code quality
    information, using `COMMAND`
    (provided by subclasses).
    """
    COMMAND = ''
    DISCOVERY_COMMAND = ''
    OPTIONS = []

    # Encoding of the stdout from the command
    # This is application-dependent
    STDOUT_ENCODING = 'utf-8'

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
                output = self._run_command(src_path)
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
            contents = file_handle.read().decode(self.STDOUT_ENCODING,
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

    def _run_command(self, src_path):
        """
        Run the quality command and return its output as a unicode string.
        """
        # Encode the path using the filesystem encoding, determined at runtime
        encoding = sys.getfilesystemencoding()
        user_options = [self.user_options] if self.user_options else []
        command = [self.COMMAND] + self.OPTIONS + user_options + [src_path.encode(encoding)]
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
        except OSError:
            sys.stderr.write(" ".join([cmd.decode(encoding)
                                       if isinstance(cmd, bytes) else cmd
                                       for cmd in command]))
            raise

        if stderr and (process.returncode != 0):
            raise QualityReporterError(stderr.decode(encoding))

        return stdout.strip().decode(self.STDOUT_ENCODING, 'replace')

    def _run_command_simple(self, command):
        """
        Returns command's exit code.
        """
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        process.communicate()
        exit_code = process.returncode
        return exit_code

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
    LEGACY_OPTIONS = ['-f', 'parseable', '--reports=no', '--include-ids=y']
    OPTIONS = MODERN_OPTIONS
    EXTENSIONS = ['py']
    DUPE_CODE_VIOLATION = 'R0801'

    # Match lines of the form:
    # path/to/file.py:123: [C0111] Missing docstring
    # path/to/file.py:456: [C0111, Foo.bar] Missing docstring
    VIOLATION_REGEX = re.compile(r'^([^:]+):(\d+): \[(\w+),? ?([^\]]*)] (.*)$')
    MULTI_LINE_VIOLATION_REGEX = re.compile(r'==(\w|.+):(.*)')
    DUPE_CODE_MESSAGE_REGEX = re.compile(r'Similar lines in (\d+) files')

    def _run_command(self, src_path):
        try:
            return super(PylintQualityReporter, self)._run_command(src_path)
        except QualityReporterError as report_error:
            # Support earlier pylint version (< 1)
            if "no such option: --msg-template" in six.text_type(report_error):
                self.OPTIONS = self.LEGACY_OPTIONS
                return super(PylintQualityReporter, self)._run_command(src_path)
            else:
                raise

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
        if self._run_command_simple(self.DISCOVERY_COMMAND) == 0:
            return
        raise EnvironmentError


class QualityReporterError(Exception):
    """
    A quality reporter command produced an error.
    """
    pass
