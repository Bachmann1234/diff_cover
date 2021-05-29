import xml.etree.ElementTree as etree
from io import StringIO

from diff_cover.git_path import GitPathTool
from diff_cover.violationsreporters.violations_reporter import XmlCoverageReporter

# https://github.com/Bachmann1234/diff_cover/issues/190
def test_get_src_path_clover():
    GitPathTool._cwd = "/"
    GitPathTool._root = "/"
    clover_report = etree.parse(
        StringIO(
            """<?xml version="1.0" encoding="UTF-8"?>
<coverage generated="1622182664251" clover="3.2.0">
  <project timestamp="1622182664251" name="All files">
    <metrics statements="8" coveredstatements="8" conditionals="6" coveredconditionals="5" methods="2" coveredmethods="2" elements="16" coveredelements="15" complexity="0" loc="8" ncloc="8" packages="2" files="2" classes="2"/>
    <package name="src">
      <metrics statements="6" coveredstatements="6" conditionals="4" coveredconditionals="4" methods="1" coveredmethods="1"/>
      <file name="isLucky.js" path="isLucky.js">
        <metrics statements="6" coveredstatements="6" conditionals="4" coveredconditionals="4" methods="1" coveredmethods="1"/>
        <line num="2" count="3" type="cond" truecount="2" falsecount="0"/>
        <line num="3" count="1" type="stmt"/>
        <line num="5" count="2" type="cond" truecount="2" falsecount="0"/>
        <line num="6" count="1" type="stmt"/>
        <line num="8" count="1" type="stmt"/>
        <line num="12" count="1" type="stmt"/>
      </file>
    </package>
    <package name="src.test">
      <metrics statements="2" coveredstatements="2" conditionals="2" coveredconditionals="1" methods="1" coveredmethods="1"/>
      <file name="isLucky2.js" path="isLucky2.js">
        <metrics statements="2" coveredstatements="2" conditionals="2" coveredconditionals="1" methods="1" coveredmethods="1"/>
        <line num="1" count="1" type="cond" truecount="1" falsecount="1"/>
        <line num="3" count="1" type="stmt"/>
      </file>
    </package>
  </project>
</coverage>"""
        )
    )
    result = XmlCoverageReporter.get_src_path_line_nodes_clover(
        clover_report, "isLucky.js"
    )
    assert sorted([int(line.attrib["num"]) for line in result]) == [2, 3, 5, 6, 8, 12]
