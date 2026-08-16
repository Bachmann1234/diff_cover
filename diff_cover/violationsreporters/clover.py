"""
Reading the ``<file>`` elements of a Clover XML coverage report.
"""

import itertools
from collections import defaultdict

from diff_cover import util
from diff_cover.git_path import GitPathTool


class CloverFileIndex:
    """
    The ``<file>`` elements of one Clover report, indexed for lookup by path.

    Building the index costs one walk of the document. Looking a source path up
    by walking the document instead costs that walk once per source path, which
    is quadratic in a report with many files.
    """

    def __init__(self, xml_document):
        """
        Index every ``<file>`` element of `xml_document`.

        A file is matched either by its path relative to the repository root
        or, when the report carries absolute paths, by a suffix test. The
        suffix can only match when the last path segment does, so candidates
        for it are grouped by that segment and the test is applied to the few
        that share it.

        Both tables store the document position of each element so that
        lookups can return matches in document order, as a direct walk would.
        """
        self._by_relative_path = defaultdict(list)
        self._by_last_segment = defaultdict(list)
        for position, file_tree in enumerate(xml_document.findall(".//file")):
            file_path = file_tree.get("path") or file_tree.get("name")
            if not file_path:
                continue

            normalized_file_path = util.to_unix_path(file_path)
            relative_file_path = util.to_unix_path(GitPathTool.relative_path(file_path))
            self._by_relative_path[relative_file_path].append((position, file_tree))
            self._by_last_segment[normalized_file_path.rsplit("/", 1)[-1]].append(
                (position, normalized_file_path, file_tree)
            )

    def _files(self, src_path):
        """
        Return the ``<file>`` elements for `src_path`, in document order.
        """
        normalized_src_path = util.to_unix_path(src_path)

        matches = {}
        for position, file_tree in self._by_relative_path.get(normalized_src_path, ()):
            matches[position] = file_tree
        suffix = f"/{normalized_src_path}"
        for position, normalized_file_path, file_tree in self._by_last_segment.get(
            normalized_src_path.rsplit("/", 1)[-1], ()
        ):
            if normalized_file_path.endswith(suffix):
                matches[position] = file_tree

        return [matches[position] for position in sorted(matches)]

    def line_nodes(self, src_path):
        """
        Return a list of nodes containing line information for `src_path`.

        If the file is not present in the report, return None
        """
        files = self._files(src_path)
        if not files:
            return None
        lines = []
        for file_tree in files:
            # Clover marks an executable line as one of these three types. PHPUnit's
            # writer emits `method` for the declaration line of every function it
            # measured; leaving it out reported those lines as unmeasured.
            # https://github.com/sebastianbergmann/php-code-coverage/blob/main/src/Report/Clover.php
            lines.append(file_tree.findall('./line[@type="method"]'))
            lines.append(file_tree.findall('./line[@type="stmt"]'))
            lines.append(file_tree.findall('./line[@type="cond"]'))
        return list(itertools.chain(*lines))
