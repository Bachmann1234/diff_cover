# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mock
import unittest
from textwrap import dedent
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool, GitDiffError
from diff_cover.tests.helpers import line_numbers, git_diff_output


class GitDiffReporterTest(unittest.TestCase):

    def setUp(self):

        # Create a mock git diff wrapper
        self._git_diff = mock.MagicMock(GitDiffTool)

        # Create the diff reporter
        self.diff = GitDiffReporter(git_diff=self._git_diff)

    def test_name(self):

        # Expect that diff report is named after its compare branch
        self.assertEqual(
            self.diff.name(), 'origin/master...HEAD, staged and unstaged changes'
        )

    def test_name_compare_branch(self):
        # Override the default branch
        self.assertEqual(
            GitDiffReporter(git_diff=self._git_diff, compare_branch='release').name(),
            'release...HEAD, staged and unstaged changes'
        )

    def test_name_ignore_staged(self):
        # Override the default branch
        self.assertEqual(
            GitDiffReporter(git_diff=self._git_diff, ignore_staged=True).name(),
            'origin/master...HEAD and unstaged changes'
        )

    def test_name_ignore_unstaged(self):
        # Override the default branch
        self.assertEqual(
            GitDiffReporter(git_diff=self._git_diff, ignore_unstaged=True).name(),
            'origin/master...HEAD and staged changes'
        )

    def test_name_ignore_staged_and_unstaged(self):
        # Override the default branch
        self.assertEqual(
            GitDiffReporter(git_diff=self._git_diff, ignore_staged=True, ignore_unstaged=True).name(),
            'origin/master...HEAD'
        )

    def test_git_exclude(self):
        self.diff = GitDiffReporter(git_diff=self._git_diff, exclude=['file1.py'])

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir1/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir2/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths
        # They should be in alphabetical order
        self.assertEqual(len(source_paths), 3)
        self.assertEqual('file3.py', source_paths[0])
        self.assertEqual('README.md', source_paths[1])
        self.assertEqual('subdir2/file2.py', source_paths[2])

    def test_git_source_paths(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths
        # They should be in alphabetical order
        self.assertEqual(len(source_paths), 4)
        self.assertEqual('file3.py', source_paths[0])
        self.assertEqual('README.md', source_paths[1])
        self.assertEqual('subdir/file1.py', source_paths[2])
        self.assertEqual('subdir/file2.py', source_paths[3])

    def test_duplicate_source_paths(self):

        # Duplicate the output for committed, staged, and unstaged changes
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output(diff, diff, diff)

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Should see only one copy of source files
        self.assertEqual(len(source_paths), 1)
        self.assertEqual('subdir/file1.py', source_paths[0])

    def test_git_source_paths_with_supported_extensions(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output({'README.md': line_numbers(3, 10)})
        )

        # Set supported extensions
        self.diff._supported_extensions = ['py']

        # Get the source paths in the diff
        source_paths = self.diff.src_paths_changed()

        # Validate the source paths, README.md should be left out
        self.assertEqual(len(source_paths), 3)
        self.assertEqual('file3.py', source_paths[0])
        self.assertEqual('subdir/file1.py', source_paths[1])
        self.assertEqual('subdir/file2.py', source_paths[2])

    def test_git_lines_changed(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) + line_numbers(34, 47))

    def test_ignore_lines_outside_src(self):

        # Add some lines at the start of the diff, before any
        # source files are specified
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10)})
        master_diff = "\n".join(['- deleted line', '+ added line', diff])

        # Configure the git diff output
        self._set_git_diff_output(master_diff, "", "")

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10))

    def test_one_line_file(self):

        # Files with only one line have a special format
        # in which the "length" part of the hunk is not specified
        diff_str = dedent("""
            diff --git a/diff_cover/one_line.txt b/diff_cover/one_line.txt
            index 0867e73..9daeafb 100644
            --- a/diff_cover/one_line.txt
            +++ b/diff_cover/one_line.txt
            @@ -1,3 +1 @@
            test
            -test
            -test
            """).strip()

        # Configure the git diff output
        self._set_git_diff_output(diff_str, "", "")

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('one_line.txt')

        # Expect that no lines are changed
        self.assertEqual(len(lines_changed), 0)

    def test_git_deleted_lines(self):

        # Configure the git diff output
        self._set_git_diff_output(
            git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}),
            git_diff_output({'subdir/file2.py': line_numbers(3, 10), 'file3.py': [0]}),
            git_diff_output(dict(), deleted_files=['README.md'])
        )

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('README.md')

        # Validate no lines changed
        self.assertEqual(len(lines_changed), 0)

    def test_git_unicode_filename(self):

        # Filenames with unicode characters have double quotes surrounding them
        # in the git diff output.
        diff_str = dedent("""
            diff --git "a/unic\303\270\342\210\202e\314\201.txt" "b/unic\303\270\342\210\202e\314\201.txt"
            new file mode 100644
            index 0000000..248ebea
            --- /dev/null
            +++ "b/unic\303\270\342\210\202e\314\201.txt"
            @@ -0,0 +1,13 @@
            +μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος
            +οὐλομένην, ἣ μυρί᾽ Ἀχαιοῖς ἄλγε᾽ ἔθηκε,
            +πολλὰς δ᾽ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν
            """).strip()

        self._set_git_diff_output(diff_str, "", "")
        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('unic\303\270\342\210\202e\314\201.txt')

        # Expect that three lines changed
        self.assertEqual(len(lines_changed), 3)

    def test_git_repeat_lines(self):

        # Same committed, staged, and unstaged lines
        diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output(diff, diff, diff)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 10) + line_numbers(34, 47))

    def test_git_overlapping_lines(self):

        master_diff = git_diff_output(
            {'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)}
        )

        # Overlap, extending the end of the hunk (lines 3 to 10)
        overlap_1 = git_diff_output({'subdir/file1.py': line_numbers(5, 14)})

        # Overlap, extending the beginning of the hunk (lines 34 to 47)
        overlap_2 = git_diff_output({'subdir/file1.py': line_numbers(32, 37)})

        # Lines in staged / unstaged overlap with lines in master
        self._set_git_diff_output(master_diff, overlap_1, overlap_2)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(3, 14) + line_numbers(32, 47))

    def test_git_line_within_hunk(self):

        master_diff = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})

        # Surround hunk in master (lines 3 to 10)
        surround = git_diff_output({'subdir/file1.py': line_numbers(2, 11)})

        # Within hunk in master (lines 34 to 47)
        within = git_diff_output({'subdir/file1.py': line_numbers(35, 46)})

        # Lines in staged / unstaged overlap with hunks in master
        self._set_git_diff_output(master_diff, surround, within)

        # Get the lines changed in the diff
        lines_changed = self.diff.lines_changed('subdir/file1.py')

        # Validate the lines changed
        self.assertEqual(lines_changed, line_numbers(2, 11) + line_numbers(34, 47))

    def test_inter_diff_conflict(self):

        # Commit changes to lines 3 through 10
        added_diff = git_diff_output({'file.py': line_numbers(3, 10)})

        # Delete the lines we modified
        deleted_lines = []
        for line in added_diff.split('\n'):

            # Any added line becomes a deleted line
            if line.startswith('+'):
                deleted_lines.append(line.replace('+', '-'))

            # No need to include lines we already deleted
            elif line.startswith('-'):
                pass

            # Keep any other line
            else:
                deleted_lines.append(line)

        deleted_diff = "\n".join(deleted_lines)

        # Try all combinations of diff conflicts
        combinations = [(added_diff, deleted_diff, ''),
                        (added_diff, '', deleted_diff),
                        ('', added_diff, deleted_diff),
                        (added_diff, deleted_diff, deleted_diff)]

        for (master_diff, staged_diff, unstaged_diff) in combinations:

            # Set up so we add lines, then delete them
            self._set_git_diff_output(master_diff, staged_diff, unstaged_diff)

            # Should have no lines changed, since
            # we deleted all the lines we modified
            fail_msg = dedent("""
            master_diff = {0}
            staged_diff = {1}
            unstaged_diff = {2}
            """).format(master_diff, staged_diff, unstaged_diff)

            self.assertEqual(self.diff.lines_changed('file.py'), [],
                             msg=fail_msg)

    def test_git_no_such_file(self):

        diff = git_diff_output({
            'subdir/file1.py': [1],
            'subdir/file2.py': [2],
            'file3.py': [3]
        })

        # Configure the git diff output
        self._set_git_diff_output(diff, "", "")

        lines_changed = self.diff.lines_changed('no_such_file.txt')
        self.assertEqual(len(lines_changed), 0)

    def test_no_diff(self):

        # Configure the git diff output
        self._set_git_diff_output('', '', '')

        # Expect no files changed
        source_paths = self.diff.src_paths_changed()
        self.assertEqual(source_paths, [])

    def test_git_diff_error(self):

        invalid_hunk_str = dedent("""
           diff --git a/subdir/file1.py b/subdir/file1.py
           @@ invalid @@ Text
        """).strip()

        no_src_line_str = "@@ -33,10 +34,13 @@ Text"

        non_numeric_lines = dedent("""
            diff --git a/subdir/file1.py b/subdir/file1.py
            @@ -1,2 +a,b @@
        """).strip()

        missing_line_num = dedent("""
            diff --git a/subdir/file1.py b/subdir/file1.py
            @@ -1,2 +  @@
        """).strip()

        missing_src_str = "diff --git "

        # List of (stdout, stderr) git diff pairs that should cause
        # a GitDiffError to be raised.
        err_outputs = [
            invalid_hunk_str, no_src_line_str,
            non_numeric_lines, missing_line_num,
            missing_src_str
        ]

        for diff_str in err_outputs:

            # Configure the git diff output
            self._set_git_diff_output(diff_str, '', '')

            # Expect that both methods that access git diff raise an error
            with self.assertRaises(GitDiffError):
                print("src_paths_changed() "
                      "should fail for {}".format(diff_str))
                self.diff.src_paths_changed()

            with self.assertRaises(GitDiffError):
                print("lines_changed() should fail for {}".format(diff_str))
                self.diff.lines_changed('subdir/file1.py')

    def test_plus_sign_in_hunk_bug(self):

        # This was a bug that caused a parse error
        diff_str = dedent("""
            diff --git a/file.py b/file.py
            @@ -16,16 +16,7 @@ 1 + 2
            + test
            + test
            + test
            + test
            """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('file.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def test_terminating_chars_in_hunk(self):

        # Check what happens when there's an @@ symbol after the
        # first terminating @@ symbol
        diff_str = dedent("""
            diff --git a/file.py b/file.py
            @@ -16,16 +16,7 @@ and another +23,2 @@ symbol
            + test
            + test
            + test
            + test
            """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('file.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def test_merge_conflict_diff(self):

        # Handle different git diff format when in the middle
        # of a merge conflict
        diff_str = dedent("""
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
        """)

        self._set_git_diff_output(diff_str, '', '')

        lines_changed = self.diff.lines_changed('subdir/src.py')
        self.assertEqual(lines_changed, [16, 17, 18, 19])

    def test_inclusion_list(self):
        unstaged_input = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output('', '', unstaged_input)

        self.assertEqual(3, len(self.diff._get_included_diff_results()))
        self.assertEqual(['', '', unstaged_input], self.diff._get_included_diff_results())

    def test_ignore_staged_inclusion(self):
        self.diff = GitDiffReporter(git_diff=self._git_diff, ignore_staged=True)

        staged_input = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output('', staged_input, '')

        self.assertEqual(2, len(self.diff._get_included_diff_results()))
        self.assertEqual(['', ''], self.diff._get_included_diff_results())

    def test_ignore_unstaged_inclusion(self):
        self.diff = GitDiffReporter(git_diff=self._git_diff, ignore_unstaged=True)

        unstaged_input = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output('', '', unstaged_input)

        self.assertEqual(2, len(self.diff._get_included_diff_results()))
        self.assertEqual(['', ''], self.diff._get_included_diff_results())

    def test_ignore_staged_and_unstaged_inclusion(self):
        self.diff = GitDiffReporter(git_diff=self._git_diff, ignore_staged=True, ignore_unstaged=True)

        staged_input = git_diff_output({'subdir/file1.py': line_numbers(3, 10) + line_numbers(34, 47)})
        unstaged_input = git_diff_output({'subdir/file2.py': line_numbers(3, 10) + line_numbers(34, 47)})
        self._set_git_diff_output('', staged_input, unstaged_input)

        self.assertEqual(1, len(self.diff._get_included_diff_results()))
        self.assertEqual([''], self.diff._get_included_diff_results())

    def test_fnmatch(self):
        """Verify that our fnmatch wrapper works as expected."""
        self.assertEqual(self.diff._fnmatch('foo.py', []), True)
        self.assertEqual(self.diff._fnmatch('foo.py', ['*.pyc']), False)
        self.assertEqual(self.diff._fnmatch('foo.pyc', ['*.pyc']), True)
        self.assertEqual(
            self.diff._fnmatch('foo.pyc', ['*.swp', '*.pyc', '*.py']), True)

    def test_fnmatch_returns_the_default_with_empty_default(self):
        """The default parameter should be returned when no patterns are given.
        """
        sentinel = object()
        self.assertTrue(
            self.diff._fnmatch('file.py', [], default=sentinel) is sentinel)

    def _set_git_diff_output(self, committed_diff,
                             staged_diff, unstaged_diff):
        """
        Configure the git diff tool to return `committed_diff`,
        `staged_diff`, and `unstaged_diff` as outputs from
        `git diff`
        """
        self.diff.clear_cache()
        self._git_diff.diff_committed.return_value = committed_diff
        self._git_diff.diff_staged.return_value = staged_diff
        self._git_diff.diff_unstaged.return_value = unstaged_diff
