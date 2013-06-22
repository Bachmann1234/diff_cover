"""
Classes for generating diff coverage reports.
"""

from abc import ABCMeta, abstractmethod
from jinja2 import Environment, PackageLoader


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

        if total_lines > 0:
            num_covered = total_lines - self.total_num_missing()
            return int(float(num_covered) / total_lines * 100)

        else:
            return 100

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


# Set up the template environment
TEMPLATE_LOADER = PackageLoader(__package__)
TEMPLATE_ENV = Environment(loader=TEMPLATE_LOADER,
                           trim_blocks=True)


class TemplateReportGenerator(BaseReportGenerator):
    """
    Reporter that uses a template to generate the report.
    """

    # Subclasses override this to specify the name of the template
    # If not overridden, the template reporter will raise an exception
    TEMPLATE_NAME = None

    def generate_report(self, output_file):
        """
        See base class.
        """

        if self.TEMPLATE_NAME is not None:

            # Find the template
            template = TEMPLATE_ENV.get_template(self.TEMPLATE_NAME)

            # Render the template
            report = template.render(self._context())

            # Write the report to the output file
            # (encode to a byte string)
            output_file.write(report.encode())

    def _context(self):
        """
        Return the context to pass to the template.

        The context is a dict of the form:

        {'report_name': REPORT_NAME,
         'diff_name': DIFF_NAME,
         'src_stats': {SRC_PATH: {
                            'percent_covered': PERCENT_COVERED,
                            'missing_lines': [LINE_NUM, ...]
                            }, ... }
         'total_num_lines': TOTAL_NUM_LINES,
         'total_num_missing': TOTAL_NUM_MISSING,
         'total_percent_covered': TOTAL_PERCENT_COVERED}
        """

        # Calculate the information to pass to the template
        src_stats = {src: self._src_path_stats(src)
                     for src in self.src_paths()}

        return {'report_name': self.coverage_report_name(),
                'diff_name': self.diff_report_name(),
                'src_stats': src_stats,
                'total_num_lines': self.total_num_lines(),
                'total_num_missing': self.total_num_missing(),
                'total_percent_covered': self.total_percent_covered()}

    def _src_path_stats(self, src_path):
        """
        Return a dict of statistics for the source file at `src_path`.
        """
        # Find missing lines
        missing_lines = [str(line) for line
                         in self.missing_lines(src_path)]

        return {'percent_covered': self.percent_covered(src_path),
                'missing_lines': missing_lines}


class StringReportGenerator(TemplateReportGenerator):
    """
    Generate a string diff coverage report.
    """

    TEMPLATE_NAME = "console_report.txt"


class HtmlReportGenerator(TemplateReportGenerator):
    """
    Generate an HTML formatted diff coverage report.
    """
    TEMPLATE_NAME = "html_report.html"
