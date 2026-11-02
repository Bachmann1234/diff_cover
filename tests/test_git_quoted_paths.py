"""Exercise Git quoting through the public coverage entrypoint."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from diff_cover import diff_cover_tool


@pytest.mark.parametrize("quote_path", [True, False])
@pytest.mark.parametrize(
    "filename",
    [
        "plain.py",
        "with space.py",
        "東京.py",
        "résumé.py",
        "📚.py",
        pytest.param(
            'résumé"notes.py',
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="Invalid Windows filename"
            ),
        ),
        pytest.param(
            "tab\tname.py",
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="Invalid Windows filename"
            ),
        ),
        pytest.param(
            "new\nline.py",
            marks=pytest.mark.skipif(
                sys.platform == "win32", reason="Invalid Windows filename"
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    "state", ["committed", "staged", "unstaged", "diff-file", "untracked"]
)
def test_coverage_for_git_quoted_paths(
    tmp_path, monkeypatch, filename, state, quote_path
):
    """Count the actual uncovered file across all supported Git input modes."""
    monkeypatch.chdir(tmp_path)

    def git(*args):
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, encoding="utf-8"
        ).stdout

    git("init")
    git("config", "user.name", "Diff Cover Test")
    git("config", "user.email", "diff-cover@example.com")
    git("config", "commit.gpgsign", "false")
    git("config", "core.quotePath", "true" if quote_path else "false")
    (tmp_path / ".gitignore").write_text(
        "coverage.xml\nreport.json\ndiff.patch\n",
    )
    source = tmp_path / filename
    if state != "untracked":
        source.write_text("value = 1\n")
    git("add", "--all")
    git("commit", "-m", "Initial source")
    git("branch", "baseline")
    source.write_text("value = 2\n")
    if state in ("staged", "committed"):
        git("add", "--", filename)
    if state == "committed":
        git("commit", "-m", "Change source")

    coverage = ET.Element("coverage")
    sources = ET.SubElement(coverage, "sources")
    ET.SubElement(sources, "source").text = str(tmp_path)
    packages = ET.SubElement(coverage, "packages")
    package = ET.SubElement(packages, "package", name="")
    cls = ET.SubElement(
        ET.SubElement(package, "classes"),
        "class",
        name=filename,
        filename=filename,
    )
    ET.SubElement(ET.SubElement(cls, "lines"), "line", number="1", hits="0")
    ET.ElementTree(coverage).write(
        "coverage.xml", encoding="utf-8", xml_declaration=True
    )

    args = [
        "diff-cover",
        "coverage.xml",
        "--compare-branch",
        "baseline",
        "--fail-under",
        "100",
        "--format",
        "json:report.json",
    ]
    if state == "diff-file":
        (tmp_path / "diff.patch").write_text(
            git("diff", "HEAD"),
            encoding="utf-8",
        )
        args.extend(["--diff-file", "diff.patch"])
    if state == "untracked":
        args.append("--include-untracked")

    assert diff_cover_tool.main(args) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["total_num_lines"] == 1
    assert report["total_num_violations"] == 1
    assert report["src_stats"][filename]["violation_lines"] == [1]
