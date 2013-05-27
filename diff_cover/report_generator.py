"""
Classes for generating diff coverage reports.
"""

from abc import ABCMeta, abstractmethod

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
        pass

    @abstractmethod
    def generate_report(self, output_file):
        """
        Write the report to `output_file`, which is a file-like
        object implementing the `write()` method.
        """
        pass

class StringReportGenerator(object):
    """
    Generate a string diff coverage report.
    """

    def generate_report(self, output_file):
        """
        Write a basic string report to `output_file`.
        """
        pass

class HtmlReportGenerator(object):
    """
    Generate an HTML formatted diff coverage report.
    """

    def generate_report(self, output_file):
        """
        Write an HTML-formatted report to `output_file`.
        """
        pass
