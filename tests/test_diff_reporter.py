# pylint: disable=missing-function-docstring,protected-access

"""Test for diff_cover.diff_reporter"""

import os
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffError, GitDiffTool
from tests.helpers import git_diff_output, line_numbers


@pytest.fixture
def git_diff(mocker):
    m = mocker.MagicMock(GitDiffTool)
    m.range_notation = "..."
    return m


@pytest.fixture
def diff(git_diff):
    return GitDiffReporter(git_diff=git_diff)


def test_name(diff):
    # Expect that diff report is named after its compare branch
    assert diff.name() == "origin/main...HEAD, staged and unstaged changes"


def test_name_compare_branch(git_diff):
    # Override the default branch
    assert (
        GitDiffReporter(git_diff=git_diff, compare_branch="release").name()
        == "release...HEAD, staged and unstaged changes"
    )


def test_name_ignore_staged(git_diff):
    # Override the default branch
    assert (
        GitDiffReporter(git_diff=git_diff, ignore_staged=True).name()
        == "origin/main...HEAD and unstaged changes"
    )


def test_name_ignore_unstaged(git_diff):
    # Override the default branch
    assert (
        GitDiffReporter(git_diff=git_diff, ignore_unstaged=True).name()
        == "origin/main...HEAD and staged changes"
    )


def test_name_ignore_staged_and_unstaged(git_diff):
    # Override the default branch
    assert (
        GitDiffReporter(
            git_diff=git_diff, ignore_staged=True, ignore_unstaged=True
        ).name()
        == "origin/main...HEAD"
    )


def test_name_include_untracked(git_diff):
    # Override the default branch
    assert (
        GitDiffReporter(git_diff=git_diff, include_untracked=True).name()
        == "origin/main...HEAD, staged, unstaged and untracked changes"
    )


@pytest.mark.parametrize(
    "include,exclude,expected",
    [
        # no include/exclude --> use all paths
        ([], [], ["file3.py", "README.md", "subdir1/file1.py", "subdir2/file2.py"]),
        # specified exclude without include
        (
            [],
            ["file1.py"],
            ["file3.py", "README.md", "subdir2/file2.py"],
        ),
        # specified include (folder) without exclude
        (["subdir1/**"], [], ["subdir1/file1.py"]),
        # specified include (file) without exclude
        (["subdir1/file1.py"], [], ["subdir1/file1.py"]),
        # specified include and exclude
        (
            ["subdir1/**", "subdir2/**"],
            ["file1.py", "file3.py"],
            ["subdir2/file2.py"],
        ),
    ],
)
def test_git_path_selection(mocker, diff, git_diff, include, exclude, expected):
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        # change the working directory into the temp directory so that globs are working
        os.chdir(tmp_dir)

        diff = GitDiffReporter(git_diff=git_diff, exclude=exclude, include=include)

        main_dir = Path(tmp_dir)
        (main_dir / "file3.py").touch()

        subdir1 = main_dir / "subdir1"
        subdir1.mkdir()
        (subdir1 / "file1.py").touch()

        subdir2 = main_dir / "subdir2"
        subdir2.mkdir()
        (subdir2 / "file2.py").touch()

        # Configure the git diff output
        _set_git_diff_output(
            diff,
            git_diff,
            git_diff_output(
                {"subdir1/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
            ),
            git_diff_output({"subdir2/file2.py": line_numbers(3, 10), "file3.py": [0]}),
            git_diff_output(dict(), deleted_files=["README.md"]),
        )

        # Get the source paths in the diff
        mocker.patch.object(os.path, "abspath", lambda path: f"{tmp_dir}/{path}")
        source_paths = diff.src_paths_changed()

        # Validate the source paths
        # They should be in alphabetical order
        assert source_paths == expected

    # change back to the previous working directory
    os.chdir(old_cwd)


def test_git_source_paths(diff, git_diff):
    # Configure the git diff output
    _set_git_diff_output(
        diff,
        git_diff,
        git_diff_output(
            {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
        ),
        git_diff_output({"subdir/file2.py": line_numbers(3, 10), "file3.py": [0]}),
        git_diff_output(dict(), deleted_files=["README.md"]),
    )

    # Get the source paths in the diff
    source_paths = diff.src_paths_changed()

    # Validate the source paths
    # They should be in alphabetical order
    assert len(source_paths) == 4
    assert source_paths[0] == "file3.py"
    assert source_paths[1] == "README.md"
    assert source_paths[2] == "subdir/file1.py"
    assert source_paths[3] == "subdir/file2.py"


def test_git_source_paths_with_space(diff, git_diff):
    _set_git_diff_output(
        diff,
        git_diff,
        git_diff_output({" weird.py": [0]}),
    )

    source_paths = diff.src_paths_changed()

    assert len(source_paths) == 1
    assert source_paths[0] == " weird.py"


def test_duplicate_source_paths(diff, git_diff):
    # Duplicate the output for committed, staged, and unstaged changes
    diff_output = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(diff, git_diff, diff_output, diff_output, diff_output)

    # Get the source paths in the diff
    source_paths = diff.src_paths_changed()

    # Should see only one copy of source files
    assert len(source_paths) == 1
    assert source_paths[0] == "subdir/file1.py"


def test_git_source_paths_with_supported_extensions(diff, git_diff):
    # Configure the git diff output
    _set_git_diff_output(
        diff,
        git_diff,
        git_diff_output(
            {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
        ),
        git_diff_output({"subdir/file2.py": line_numbers(3, 10), "file3.py": [0]}),
        git_diff_output({"README.md": line_numbers(3, 10)}),
    )

    # Set supported extensions
    diff._supported_extensions = ["py"]

    # Get the source paths in the diff
    source_paths = diff.src_paths_changed()

    # Validate the source paths, README.md should be left out
    assert len(source_paths) == 3
    assert source_paths[0] == "file3.py"
    assert source_paths[1] == "subdir/file1.py"
    assert source_paths[2] == "subdir/file2.py"


def test_git_lines_changed(diff, git_diff):
    # Configure the git diff output
    _set_git_diff_output(
        diff,
        git_diff,
        git_diff_output(
            {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
        ),
        git_diff_output({"subdir/file2.py": line_numbers(3, 10), "file3.py": [0]}),
        git_diff_output(dict(), deleted_files=["README.md"]),
    )

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("subdir/file1.py")

    # Validate the lines changed
    assert lines_changed == line_numbers(3, 10) + line_numbers(34, 47)


def test_ignore_lines_outside_src(diff, git_diff):
    # Add some lines at the start of the diff, before any
    # source files are specified
    diff_output = git_diff_output({"subdir/file1.py": line_numbers(3, 10)})
    main_diff = "\n".join(["- deleted line", "+ added line", diff_output])

    # Configure the git diff output
    _set_git_diff_output(diff, git_diff, main_diff, "", "")

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("subdir/file1.py")

    # Validate the lines changed
    assert lines_changed == line_numbers(3, 10)


def test_one_line_file(diff, git_diff):
    # Files with only one line have a special format
    # in which the "length" part of the hunk is not specified
    diff_str = dedent(
        """
        diff --git a/diff_cover/one_line.txt b/diff_cover/one_line.txt
        index 0867e73..9daeafb 100644
        --- a/diff_cover/one_line.txt
        +++ b/diff_cover/one_line.txt
        @@ -1,3 +1 @@
        test
        -test
        -test
        """
    ).strip()

    # Configure the git diff output
    _set_git_diff_output(diff, git_diff, diff_str, "", "")

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("one_line.txt")

    # Expect that no lines are changed
    assert len(lines_changed) == 0


def test_git_deleted_lines(diff, git_diff):
    # Configure the git diff output
    _set_git_diff_output(
        diff,
        git_diff,
        git_diff_output(
            {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
        ),
        git_diff_output({"subdir/file2.py": line_numbers(3, 10), "file3.py": [0]}),
        git_diff_output(dict(), deleted_files=["README.md"]),
    )

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("README.md")

    # Validate no lines changed
    assert len(lines_changed) == 0


def test_git_unicode_filename(diff, git_diff):
    # Filenames with unicode characters have double quotes surrounding them
    # in the git diff output.
    diff_str = dedent(
        """
        diff --git "a/unic\303\270\342\210\202e\314\201.txt" "b/unic\303\270\342\210\202e\314\201.txt"
        new file mode 100644
        index 0000000..248ebea
        --- /dev/null
        +++ "b/unic\303\270\342\210\202e\314\201.txt"
        @@ -0,0 +1,13 @@
        +μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος
        +οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε,
        +πολλὰς δ᾽ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν
        """
    ).strip()

    _set_git_diff_output(diff, git_diff, diff_str, "", "")
    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("unic\303\270\342\210\202e\314\201.txt")

    # Expect that three lines changed
    assert len(lines_changed) == 3


def test_git_repeat_lines(diff, git_diff):
    # Same committed, staged, and unstaged lines
    diff_output = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(diff, git_diff, diff_output, diff_output, diff_output)

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("subdir/file1.py")

    # Validate the lines changed
    assert lines_changed == line_numbers(3, 10) + line_numbers(34, 47)


def test_git_overlapping_lines(diff, git_diff):
    main_diff = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )

    # Overlap, extending the end of the hunk (lines 3 to 10)
    overlap_1 = git_diff_output({"subdir/file1.py": line_numbers(5, 14)})

    # Overlap, extending the beginning of the hunk (lines 34 to 47)
    overlap_2 = git_diff_output({"subdir/file1.py": line_numbers(32, 37)})

    # Lines in staged / unstaged overlap with lines in main
    _set_git_diff_output(diff, git_diff, main_diff, overlap_1, overlap_2)

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("subdir/file1.py")

    # Validate the lines changed
    assert lines_changed == line_numbers(3, 14) + line_numbers(32, 47)


def test_git_line_within_hunk(diff, git_diff):
    main_diff = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )

    # Surround hunk in main (lines 3 to 10)
    surround = git_diff_output({"subdir/file1.py": line_numbers(2, 11)})

    # Within hunk in main (lines 34 to 47)
    within = git_diff_output({"subdir/file1.py": line_numbers(35, 46)})

    # Lines in staged / unstaged overlap with hunks in main
    _set_git_diff_output(diff, git_diff, main_diff, surround, within)

    # Get the lines changed in the diff
    lines_changed = diff.lines_changed("subdir/file1.py")

    # Validate the lines changed
    assert lines_changed == line_numbers(2, 11) + line_numbers(34, 47)


def test_inter_diff_conflict(diff, git_diff):
    # Commit changes to lines 3 through 10
    added_diff = git_diff_output({"file.py": line_numbers(3, 10)})

    # Delete the lines we modified
    deleted_lines = []
    for line in added_diff.split("\n"):

        # Any added line becomes a deleted line
        if line.startswith("+"):
            deleted_lines.append(line.replace("+", "-"))

        # No need to include lines we already deleted
        elif line.startswith("-"):
            pass

        # Keep any other line
        else:
            deleted_lines.append(line)

    deleted_diff = "\n".join(deleted_lines)

    # Try all combinations of diff conflicts
    combinations = [
        (added_diff, deleted_diff, ""),
        (added_diff, "", deleted_diff),
        ("", added_diff, deleted_diff),
        (added_diff, deleted_diff, deleted_diff),
    ]

    for (main_diff, staged_diff, unstaged_diff) in combinations:
        # Set up so we add lines, then delete them
        _set_git_diff_output(diff, git_diff, main_diff, staged_diff, unstaged_diff)
        assert diff.lines_changed("file.py") == []


def test_git_no_such_file(diff, git_diff):
    diff_output = git_diff_output(
        {"subdir/file1.py": [1], "subdir/file2.py": [2], "file3.py": [3]}
    )

    # Configure the git diff output
    _set_git_diff_output(diff, git_diff, diff_output, "", "")

    lines_changed = diff.lines_changed("no_such_file.txt")
    assert len(lines_changed) == 0


def test_no_diff(diff, git_diff):
    # Configure the git diff output
    _set_git_diff_output(diff, git_diff, "", "", "")

    # Expect no files changed
    source_paths = diff.src_paths_changed()
    assert source_paths == []


def test_git_diff_error(
    diff,
    git_diff,
):
    invalid_hunk_str = dedent(
        """
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ invalid @@ Text
    """
    ).strip()

    no_src_line_str = "@@ -33,10 +34,13 @@ Text"

    non_numeric_lines = dedent(
        """
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -1,2 +a,b @@
    """
    ).strip()

    missing_line_num = dedent(
        """
        diff --git a/subdir/file1.py b/subdir/file1.py
        @@ -1,2 +  @@
    """
    ).strip()

    missing_src_str = "diff --git "

    # List of (stdout, stderr) git diff pairs that should cause
    # a GitDiffError to be raised.
    err_outputs = [
        invalid_hunk_str,
        no_src_line_str,
        non_numeric_lines,
        missing_line_num,
        missing_src_str,
    ]

    for diff_str in err_outputs:

        # Configure the git diff output
        _set_git_diff_output(diff, git_diff, diff_str, "", "")

        # Expect that both methods that access git diff raise an error
        with pytest.raises(GitDiffError):
            print("src_paths_changed() " "should fail for {}".format(diff_str))
            diff.src_paths_changed()

        with pytest.raises(GitDiffError):
            print(f"lines_changed() should fail for {diff_str}")
            diff.lines_changed("subdir/file1.py")


def test_plus_sign_in_hunk_bug(diff, git_diff):
    # This was a bug that caused a parse error
    diff_str = dedent(
        """
        diff --git a/file.py b/file.py
        @@ -16,16 +16,7 @@ 1 + 2
        + test
        + test
        + test
        + test
        """
    )

    _set_git_diff_output(diff, git_diff, diff_str, "", "")

    lines_changed = diff.lines_changed("file.py")
    assert lines_changed == [16, 17, 18, 19]


def test_terminating_chars_in_hunk(diff, git_diff):
    # Check what happens when there's an @@ symbol after the
    # first terminating @@ symbol
    diff_str = dedent(
        """
        diff --git a/file.py b/file.py
        @@ -16,16 +16,7 @@ and another +23,2 @@ symbol
        + test
        + test
        + test
        + test
        """
    )

    _set_git_diff_output(diff, git_diff, diff_str, "", "")

    lines_changed = diff.lines_changed("file.py")
    assert lines_changed == [16, 17, 18, 19]


def test_merge_conflict_diff(diff, git_diff):
    # Handle different git diff format when in the middle
    # of a merge conflict
    diff_str = dedent(
        """
        diff --cc subdir/src.py
        index d2034c0,e594d54..0000000
        diff --cc subdir/src.py
        index d2034c0,e594d54..0000000
        --- a/subdir/src.py
        +++ b/subdir/src.py
        @@@ -16,88 -16,222 +16,7 @@@ text
        + test
        ++<<<<<< HEAD
        + test
        ++=======
    """
    )

    _set_git_diff_output(diff, git_diff, diff_str, "", "")

    lines_changed = diff.lines_changed("subdir/src.py")
    assert lines_changed == [16, 17, 18, 19]


def test_inclusion_list(diff, git_diff):
    unstaged_input = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(diff, git_diff, "", "", unstaged_input)

    assert len(diff._get_included_diff_results()) == 3
    assert ["", "", unstaged_input] == diff._get_included_diff_results()


def test_ignore_staged_inclusion(git_diff):
    reporter = GitDiffReporter(git_diff=git_diff, ignore_staged=True)

    staged_input = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(reporter, git_diff, "", staged_input, "")

    assert reporter._get_included_diff_results() == ["", ""]


def test_ignore_unstaged_inclusion(git_diff):
    reporter = GitDiffReporter(git_diff=git_diff, ignore_unstaged=True)

    unstaged_input = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(reporter, git_diff, "", "", unstaged_input)

    assert reporter._get_included_diff_results() == ["", ""]


def test_ignore_staged_and_unstaged_inclusion(git_diff):
    reporter = GitDiffReporter(
        git_diff=git_diff, ignore_staged=True, ignore_unstaged=True
    )

    staged_input = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    unstaged_input = git_diff_output(
        {"subdir/file2.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(reporter, git_diff, "", staged_input, unstaged_input)

    assert reporter._get_included_diff_results() == [""]


def test_fnmatch(diff):
    """Verify that our fnmatch wrapper works as expected."""
    assert diff._fnmatch("foo.py", [])
    assert not diff._fnmatch("foo.py", ["*.pyc"])
    assert diff._fnmatch("foo.pyc", ["*.pyc"])
    assert diff._fnmatch("foo.pyc", ["*.swp", "*.pyc", "*.py"])


def test_fnmatch_returns_the_default_with_empty_default(diff):
    """The default parameter should be returned when no patterns are given."""
    sentinel = object()
    assert diff._fnmatch("file.py", [], default=sentinel) is sentinel


def test_include_untracked(mocker, git_diff):
    reporter = GitDiffReporter(git_diff=git_diff, include_untracked=True)
    diff_output = git_diff_output(
        {"subdir/file1.py": line_numbers(3, 10) + line_numbers(34, 47)}
    )
    _set_git_diff_output(
        reporter, git_diff, staged_diff=diff_output, untracked=["u1.py", " u2.py"]
    )

    open_mock = mocker.mock_open(read_data="1\n2\n3\n")
    mocker.patch("diff_cover.diff_reporter.open", open_mock)
    changed = reporter.src_paths_changed()

    assert sorted(changed) == [" u2.py", "subdir/file1.py", "u1.py"]
    assert reporter.lines_changed("u1.py") == [1, 2, 3]
    assert reporter.lines_changed(" u2.py") == [1, 2, 3]


def _set_git_diff_output(
    reporter,
    diff_tool,
    committed_diff="",
    staged_diff="",
    unstaged_diff="",
    untracked=None,
):
    """
    Configure the git diff tool to return `committed_diff`,
    `staged_diff`, and `unstaged_diff` as outputs from
    `git diff`
    """
    reporter.clear_cache()
    diff_tool.diff_committed.return_value = committed_diff
    diff_tool.diff_staged.return_value = staged_diff
    diff_tool.diff_unstaged.return_value = unstaged_diff
    diff_tool.untracked.return_value = untracked


def test_name_with_default_range(git_diff):
    reporter = GitDiffReporter(git_diff=git_diff, ignore_staged=True)
    assert reporter.name() == "origin/main...HEAD and unstaged changes"


def test_name_different_range(mocker):
    diff = mocker.MagicMock(GitDiffTool)
    diff.range_notation = ".."
    reporter = GitDiffReporter(git_diff=diff, ignore_staged=True)
    assert reporter.name() == "origin/main..HEAD and unstaged changes"
