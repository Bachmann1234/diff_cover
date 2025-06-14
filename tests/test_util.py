import sys

import pytest

from diff_cover import util


def test_to_unix_path():
    """
    Ensure the _to_unix_path static function handles paths properly.
    """
    assert util.to_unix_path("foo/bar") == "foo/bar"
    assert util.to_unix_path("foo\\bar") == "foo/bar"
    if sys.platform.startswith("win"):
        assert util.to_unix_path("FOO\\bar") == "foo/bar"


def test_to_unescaped_filename():
    """Test the to_unescaped_filename function."""
    assert util.to_unescaped_filename('"\\\\\\\\"') == "\\\\"
    assert util.to_unescaped_filename('"\\\\"') == "\\"
    assert util.to_unescaped_filename('"\\"\\\\"') == '"\\'
    assert util.to_unescaped_filename('"\\""') == '"'
    assert util.to_unescaped_filename("some_file.py") == "some_file.py"
    assert util.to_unescaped_filename("#$%") == "#$%"


def test_open_file(tmp_path):
    """Test the open_file function."""
    with util.open_file(tmp_path / "some_file.txt", "w") as f:
        f.write("test")
    with util.open_file(tmp_path / "some_file.txt", "r") as f:
        assert f.read() == "test"
    with util.open_file(tmp_path / "some_file.txt", "wb") as f:
        f.write(b"test")
    with util.open_file(tmp_path / "some_file.txt", "rb") as f:
        assert f.read() == b"test"


@pytest.mark.usefixtures("capsys")
def test_open_file_sys_std():
    """Test the open_file function."""
    with util.open_file("-", "w") as f:
        assert f == sys.stdout
    with util.open_file("/dev/stdout", "bw") as f:
        assert f == sys.stdout.buffer
    with util.open_file("/dev/stderr", "w") as f:
        assert f == sys.stderr
    with util.open_file("/dev/stderr", "bw") as f:
        assert f == sys.stderr.buffer


def test_open_file_encoding(tmp_path):
    """Test the open_file function with encoding."""
    with util.open_file(tmp_path / "some_file.txt", "w", encoding="utf-16") as f:
        assert f.encoding == "utf-16"
        f.write("café naïve résumé")

    with util.open_file(tmp_path / "some_file.txt", "r", encoding="utf-16") as f:
        assert f.encoding == "utf-16"
        assert f.read() == "café naïve résumé"

    with pytest.raises(UnicodeDecodeError):
        with util.open_file(tmp_path / "some_file.txt", "r", encoding="utf-8") as f:
            f.read()


def test_open_file_encoding_binary(tmp_path):
    """Test the open_file function with encoding in binary mode."""
    with util.open_file(tmp_path / "some_file.txt", "bw", encoding="utf-16") as f:
        assert not hasattr(f, "encoding")
        f.write(b"cafe naive resume")

    with util.open_file(tmp_path / "some_file.txt", "br", encoding="utf-16") as f:
        assert not hasattr(f, "encoding")
        assert f.read() == b"cafe naive resume"
