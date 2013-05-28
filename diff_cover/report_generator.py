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
        and `diff_reporter` (of type BaseDiffReporter)"""
        self._coverage = coverage_reporter
        self._diff = diff_reporter

    @abstractmethod
    def generate_report(self, output_file):
        """
        Write the report to `output_file`, which is a file-like
        object implementing the `write()` method.

        Concrete subclasses should use `diff_line_coverage()`
        to get the required information.
        """
        pass

    def diff_coverage(self):
        """
        Returns a dictionary of the form:

            { SRC_PATH: { LINE_NUM: True | False } }
        
        where `SRC_PATH` is the path to the source file,
        `LINE_NUM` is the line number in the source
        file included in the diff, and the value
        indicates whether the line is covered or uncovered.
        """

        # Create a dict to store the results
        cover_dict = dict()

        # For each modified file in the diff
        for src_path in self._diff.src_paths_changed():

            # For each hunk changed
            hunks = self._diff.hunks_changed(src_path)
            for (start_line, end_line) in hunks:

                # Retrieve line coverage information
                line_cover = self._coverage.coverage_info(src_path, 
                                                          start_line, 
                                                          end_line)

                # Include only files with coverage information
                if len(line_cover) > 0:
                    cover_dict[src_path] = line_cover

        return cover_dict

def _percent_covered(line_cover_dict):
    """
    Calculate percent coverage given a line coverage dict
    of the form `{ LINE_NUM: True | False }`

    Returns an integer.
    """
    num_covered = sum([1 if covered else 0 
                  for covered in line_cover_dict.values()])

    percent_covered = int(float(num_covered) / len(line_cover_dict) * 100)

    return percent_covered

def _missing_lines(line_cover_dict):
    """
    Calculate missing lines given a line coverage dict
    of the form `{ LINE_NUM: True | False }`

    Returns an ordered list of integers representing the line numbers.
    """
    # Get all lines that are not covered, using None to indicate
    # that the line is not included
    missing_lines = [ str(line_num) if not covered else None
                      for (line_num, covered) in line_cover_dict.items()]

    # Filter out `None` values
    missing_lines = filter(lambda x: x is not None, missing_lines)

    # Sort and return
    return sorted(missing_lines)

class StringReportGenerator(BaseReportGenerator):
    """
    Generate a string diff coverage report.
    """

    def generate_report(self, output_file):
        """
        Write a basic string report to `output_file`.
        """

        # Calculate coverage for lines in the diff
        cover_info = self.diff_coverage()

        # Header line
        output_file.write("Diff Coverage\n-------------\n")

        # Source file info
        for (src_path, line_dict) in cover_info.items():

            # Calculate percent coverage
            percent_covered = _percent_covered(line_dict)

            # Find missing lines
            missing_lines = _missing_lines(line_dict)

            # Print the info
            if percent_covered < 100.0:
                info_str = "{0} ({1}%): Missing line(s) {2}\n".format(\
                            src_path, percent_covered, 
                            ",".join(missing_lines))
            else:
                info_str = "{0} (100%)\n".format(src_path)

            output_file.write(info_str)

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

        # Calculate coverage for lines in the diff
        cover_info = self.diff_coverage()

        # Header 
        output_file.write(self.DOCTYPE + '\n')
        output_file.write('<html>\n<head>\n')
        output_file.write(self.META + '\n')
        output_file.write(self.TITLE + '\n')
        output_file.write('</head>\n')

        # Body
        output_file.write('<body>\n')
        output_file.write(self.CONTENT_TITLE + '\n')
        output_file.write(self.TABLE_HEADER + '\n')

        # Source file information
        for (src_path, line_dict) in cover_info.items():

            # Calculate percent coverage
            percent_covered = _percent_covered(line_dict)

            # Find missing lines
            missing_lines = _missing_lines(line_dict)

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

        # Closing tags
        output_file.write('</table>\n</body>\n</html>')
