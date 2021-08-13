import sys

from diff_cover import util


def test_to_unix_path():
    """
    Ensure the _to_unix_path static function handles paths properly.
    """
    assert util.to_unix_path("foo/bar") == "foo/bar"
    assert util.to_unix_path("foo\\bar") == "foo/bar"
    if sys.platform.startswith("win"):
        assert util.to_unix_path("FOO\\bar") == "foo/bar"
