# pylint: disable=missing-function-docstring,protected-access

"""Test for diff_cover.violationsreporters - clover"""

import xml.etree.ElementTree as ET

from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.violations_reporter import XmlCoverageReporter


# https://github.com/Bachmann1234/diff_cover/issues/190
def test_get_src_path_clover(datadir, monkeypatch):
    monkeypatch.setattr(GitPathTool, "_cwd", "/")
    monkeypatch.setattr(GitPathTool, "_root", "/")

    clover_report = ET.parse(str(datadir / "test.xml"))
    result = XmlCoverageReporter.get_src_path_line_nodes_clover(
        clover_report, "isLucky.js"
    )
    assert sorted([int(line.attrib["num"]) for line in result]) == [2, 3, 5, 6, 8, 12]
