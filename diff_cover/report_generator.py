"""
Classes for generating diff coverage reports.
"""

from abc import ABCMeta, abstractmethod
from textwrap import dedent


class BaseReportGenerator(object):
    """
    Generate a diff coverage report.
    """

    __metaclass__ = ABCMeta

    def __init__(self, coverage_reporter, diff_reporter):
        """
        Configure the report generator to build a report
        from `coverage_reporter` (of type BaseCoverageReporter)
        and `diff_reporter` (of type BaseDiffReporter)
        """
        self._coverage = coverage_reporter
        self._diff = diff_reporter

        self._cache_coverage = None

    @abstractmethod
    def generate_report(self, output_file):
        """
        Write the report to `output_file`, which is a file-like
        object implementing the `write()` method.

        Concrete subclasses should access diff coverage info
        using the base class methods.
        """
        pass

    def coverage_report_name(self):
        """
        Return the name of the coverage report.
        """
        return self._coverage.name()

    def diff_report_name(self):
        """
        Return the name of the diff.
        """
        return self._diff.name()

    def src_paths(self):
        """
        Return a list of source files in the diff
        for which we have coverage information.
        """
        return self._diff_coverage().keys()

    def percent_covered(self, src_path):
        """
        Return an integer percent of lines covered for the source
        in `src_path`.

        If we have no coverage information for `src_path`, returns None
        """
        line_cover_dict = self._diff_coverage().get(src_path)

        if line_cover_dict is None:
            return None

        else:
            num_covered = sum([1 if covered else 0
                          for covered in line_cover_dict.values()])

            covered = float(num_covered) / len(line_cover_dict)
            percent_covered = int(covered * 100)

            return percent_covered

    def missing_lines(self, src_path):
        """
        Return a list of missing lines (integers) in `src_path`.

        If we have no coverage information for `src_path`, returns
        an empty list.
        """

        line_cover_dict = self._diff_coverage().get(src_path)

        if line_cover_dict is None:
            return []

        else:
            # Get all lines that are not covered, using None to indicate
            # that the line is not included
            missing_lines = [int(line_num) if not covered else None
                              for (line_num, covered)
                              in line_cover_dict.items()]

            # Filter out `None` values
            missing_lines = [x for x in missing_lines if x is not None]

            # Sort and return
            return sorted(missing_lines)

    def total_num_lines(self):
        """
        Return the total number of lines in the diff for
        which we have coverage info.
        """
        return sum([len(line_cover_dict) for line_cover_dict
                    in self._diff_coverage().values()])

    def total_num_missing(self):
        """
        Returns the total number of lines in the diff
        that should be covered, but aren't.
        """

        total_missing = 0

        # For each source file in the coverage report
        for line_cover_dict in self._diff_coverage().values():

            # Line cover dict maps line numbers to True/False values
            # indicating whether the line is covered
            total_missing += sum([1 if not is_covered else 0
                                 for is_covered in line_cover_dict.values()])

        return total_missing

    def total_percent_covered(self):
        """
        Returns the percent of lines in the diff that are covered.
        (only counting lines for which we have coverage info).
        """
        total_lines = self.total_num_lines()
        num_covered = total_lines - self.total_num_missing()
        return int(float(num_covered) / total_lines * 100)

    def _diff_coverage(self):
        """
        Returns a dictionary of the form:

            { SRC_PATH: { LINE_NUM: True | False } }

        where `SRC_PATH` is the path to the source file,
        `LINE_NUM` is the line number in the source
        file included in the diff, and the value
        indicates whether the line is covered or uncovered.

        To make this efficient, we cache and reuse the result.
        """

        # If we have a cached coverage dict, return it
        if self._cache_coverage is not None:
            return self._cache_coverage

        # Otherwise, construct the dict and cache it
        else:

            # Create a dict to store the results
            cover_dict = dict()

            # For each modified file in the diff
            for src_path in self._diff.src_paths_changed():

                # For each line changed
                diff_lines = self._diff.lines_changed(src_path)
                line_cover = self._coverage.coverage_info(src_path, diff_lines)

                # Include only files with coverage information
                if len(line_cover) > 0:
                    cover_dict[src_path] = line_cover

            # Cache the result
            self._cache_coverage = cover_dict

            # Return the result
            return cover_dict


class StringReportGenerator(BaseReportGenerator):
    """
    Generate a string diff coverage report.
    """

    def generate_report(self, output_file):
        """
        Write a basic string report to `output_file`.
        """

        # Header line
        self._print_divider(output_file)
        output_file.write("Diff Coverage\n")
        output_file.write("Coverage Report: {0}\n".format(
                          self.coverage_report_name()))
        output_file.write("Diff: {0}\n".format(
                          self.diff_report_name()))
        self._print_divider(output_file)

        # If no coverage information, explain this
        if len(self.src_paths()) == 0:
            msg = "No lines with coverage information in this diff.\n"
            output_file.write(msg)

        else:

            # Source file stats
            for src_path in self.src_paths():
                self._print_src_path_stats(src_path, output_file)

            # Summary stats
            self._print_divider(output_file)
            self._print_summary_stats(output_file)

        self._print_divider(output_file)

    @staticmethod
    def _print_divider(output_file):
        """
        Print a divider line to `output_file`.
        """
        output_file.write("-------------\n")

    def _print_src_path_stats(self, src_path, output_file):
        """
        Print statistics about the source file at `src_path`.
        `output_file` is the file to write to.
        """
        # Calculate percent coverage
        percent_covered = self.percent_covered(src_path)

        # Find missing lines
        missing_lines = [str(line) for line
                         in self.missing_lines(src_path)]

        # Print the info
        if percent_covered < 100.0:
            info_str = "{0} ({1}%): Missing line(s) {2}\n".format(\
                        src_path, percent_covered,
                        ",".join(missing_lines))
        else:
            info_str = "{0} (100%)\n".format(src_path)

        output_file.write(info_str)

    def _print_summary_stats(self, output_file):
        """
        Print statistics summarizing the coverage of the entire diff.
        `output_file` is the file to write to.
        """

        info_str = dedent("""
        Total:   {0} line(s)
        Missing: {1} line(s)
        Coverage: {2}%
        """.format(self.total_num_lines(),
                   self.total_num_missing(),
                   self.total_percent_covered())).strip()

        output_file.write(info_str + "\n")


class HtmlReportGenerator(BaseReportGenerator):
    """
    Generate an HTML formatted diff coverage report.
    """

    DOCTYPE = ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" ' +
              '"http://www.w3.org/TR/html4/strict.dtd">')

    META = ("<meta http-equiv='Content-Type' " +
            "content='text/html; charset=utf-8'>")

    TITLE = "<title>Diff Coverage</title>"
    CONTENT_TITLE = "<h1>Diff Coverage</h1>"
    TABLE_HEADER = ('<table border="1">\n' +
                    '<tr>\n<th>Source File</th>\n' +
                    '<th>Diff Coverage (%)</th>\n' +
                    '<th>Missing Line(s)</th>\n</tr>')

    def generate_report(self, output_file):
        """
        Write an HTML-formatted report to `output_file`.
        """

        # Header
        output_file.write(self.DOCTYPE + '\n')
        output_file.write('<html>\n<head>\n')
        output_file.write(self.META + '\n')
        output_file.write(self.TITLE + '\n')
        output_file.write('</head>\n')

        # Body
        output_file.write('<body>\n')
        output_file.write(self.CONTENT_TITLE + '\n')

        # Source report names
        output_file.write("<p>Coverage Report: {0}</p>\n".format(
                         self.coverage_report_name()))
        output_file.write("<p>Diff: {0}</p>\n".format(
                         self.diff_report_name()))

        # If no coverage information, explain this
        if len(self.src_paths()) == 0:
            msg = "<p>No lines with coverage information in this diff.</p>\n"
            output_file.write(msg)

        else:

            # Start the table
            output_file.write(self.TABLE_HEADER + '\n')

            # Source file information
            for src_path in self.src_paths():
                self._print_src_path_stats(src_path, output_file)

            # Close the table
            output_file.write('</table>\n')

            # Summary stats
            self._print_summary_stats(output_file)

        # Closing tags
        output_file.write('</body>\n</html>')

    def _print_src_path_stats(self, src_path, output_file):
        """
        Print statistics about the source file at `src_path`.
        `output_file` is the file to write to.
        """
        # Calculate percent coverage
        percent_covered = self.percent_covered(src_path)

        # Find missing lines
        missing_lines = [str(line) for line
                         in self.missing_lines(src_path)]

        # Print the info
        if percent_covered < 100.0:
            info_str = dedent("""
            <tr>
            <td>{0}</td>
            <td>{1}%</td>
            <td>{2}</td>
            </tr>""".format(src_path, percent_covered,
                            ",".join(missing_lines))).strip()
        else:
            info_str = dedent("""
            <tr>
            <td>{0}</td>
            <td>100%</td>
            <td>&nbsp;</td>
            </tr>""".format(src_path)).strip()

        output_file.write(info_str + '\n')

    def _print_summary_stats(self, output_file):
        """
        Print statistics summarizing the coverage of the entire diff.
        `output_file` is the file to write to.
        """
        info_str = dedent("""
        <ul>
        <li><b>Total</b>: {0} line(s)</li>
        <li><b>Missing</b>: {1} line(s)</li>
        <li><b>Coverage</b>: {2}%</li>
        </ul>
        """.format(self.total_num_lines(),
                   self.total_num_missing(),
                   self.total_percent_covered())).strip()

        output_file.write(info_str + '\n')
