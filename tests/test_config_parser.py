import pytest

from diff_cover import config_parser
from diff_cover.config_parser import ParserError, TOMLParser, Tool, get_config

tools = pytest.mark.parametrize("tool", list(Tool))


class TestTOMLParser:
    @tools
    def test_parse_no_toml_file(self, tool):
        parser = TOMLParser("myfile", tool)
        assert parser.parse() is None

    @tools
    def test_parse_but_no_tomli_installed(self, tool, mocker):
        mocker.patch.object(config_parser, "_HAS_TOML", False)
        parser = TOMLParser("myfile.toml", tool)
        with pytest.raises(ParserError):
            parser.parse()

    @pytest.mark.parametrize(
        "tool,content",
        [
            (Tool.DIFF_COVER, ""),
            (Tool.DIFF_COVER, "[tool.diff_quality]"),
            (Tool.DIFF_QUALITY, ""),
            (Tool.DIFF_COVER, "[tool.diff_cover]"),
        ],
    )
    def test_parse_but_no_data(self, tool, content, tmp_path):
        toml_file = tmp_path / "foo.toml"
        toml_file.write_text(content)

        parser = TOMLParser(str(toml_file), tool)
        with pytest.raises(ParserError):
            parser.parse()

    @pytest.mark.parametrize(
        "tool,content,expected",
        [
            (Tool.DIFF_COVER, "[tool.diff_cover]\nquiet=true", {"quiet": True}),
            (Tool.DIFF_QUALITY, "[tool.diff_quality]\nquiet=true", {"quiet": True}),
        ],
    )
    def test_parse(self, tool, content, tmp_path, expected):
        toml_file = tmp_path / "foo.toml"
        toml_file.write_text(content)

        parser = TOMLParser(str(toml_file), tool)
        assert parser.parse() == expected


@tools
def test_get_config_unrecognized_file(mocker, tool):
    parser = mocker.Mock()
    parser.parse_args().__dict__ = {"config_file": "foo.bar"}
    with pytest.raises(ParserError):
        get_config(parser, argv=[], defaults={}, tool=tool)


@pytest.mark.parametrize(
    "tool,cli_config,defaults,file_content,expected",
    [
        (
            Tool.DIFF_COVER,
            {"a": 2, "b": None, "c": None},
            {"a": 4, "b": 3},
            None,
            {"a": 2, "b": 3, "c": None},
        ),
        (
            Tool.DIFF_QUALITY,
            {"a": 2, "b": None, "c": None},
            {"a": 4, "b": 3},
            None,
            {"a": 2, "b": 3, "c": None},
        ),
        (
            Tool.DIFF_COVER,
            {"a": 2, "b": None, "c": None, "d": None},
            {"a": 4, "b": 3},
            "[tool.diff_cover]\na=1\nd=6",
            {"a": 2, "b": 3, "c": None, "d": 6},
        ),
    ],
)
def test_get_config(
    mocker, tmp_path, tool, cli_config, defaults, file_content, expected
):
    if file_content:
        toml_file = tmp_path / "foo.toml"
        toml_file.write_text(file_content)
        cli_config["config_file"] = expected["config_file"] = str(toml_file)
    else:
        cli_config["config_file"] = expected["config_file"] = None

    parser = mocker.Mock()
    parser.parse_args().__dict__ = cli_config
    assert get_config(parser, argv=[], defaults=defaults, tool=tool) == expected


@pytest.mark.parametrize(
    "tool,content,expected_exclude",
    [
        (Tool.DIFF_COVER, '[tool.diff_cover]\nexclude="*.pyc"', ["*.pyc"]),
        (Tool.DIFF_QUALITY, '[tool.diff_quality]\nexclude="*.pyc"', ["*.pyc"]),
    ],
)
def test_normalize_exclude_string(mocker, tmp_path, tool, content, expected_exclude):
    """String exclude from TOML should be normalized to list."""
    toml_file = tmp_path / "foo.toml"
    toml_file.write_text(content)

    cli_config = {"config_file": str(toml_file), "exclude": None}
    parser = mocker.Mock()
    parser.parse_args().__dict__ = cli_config

    result = get_config(parser, argv=[], defaults={}, tool=tool)
    assert result["exclude"] == expected_exclude


@pytest.mark.parametrize(
    "tool,content,expected_exclude",
    [
        (
            Tool.DIFF_COVER,
            '[tool.diff_cover]\nexclude=["*.pyc", "*.pyo"]',
            ["*.pyc", "*.pyo"],
        ),
        (
            Tool.DIFF_QUALITY,
            '[tool.diff_quality]\nexclude=["*.pyc", "*.pyo"]',
            ["*.pyc", "*.pyo"],
        ),
    ],
)
def test_exclude_list_unchanged(mocker, tmp_path, tool, content, expected_exclude):
    """List exclude from TOML should remain as list."""
    toml_file = tmp_path / "foo.toml"
    toml_file.write_text(content)

    cli_config = {"config_file": str(toml_file), "exclude": None}
    parser = mocker.Mock()
    parser.parse_args().__dict__ = cli_config

    result = get_config(parser, argv=[], defaults={}, tool=tool)
    assert result["exclude"] == expected_exclude


@pytest.mark.parametrize(
    "tool,content,expected_include",
    [
        (Tool.DIFF_COVER, '[tool.diff_cover]\ninclude="src/**"', ["src/**"]),
        (Tool.DIFF_QUALITY, '[tool.diff_quality]\ninclude="src/**"', ["src/**"]),
    ],
)
def test_normalize_include_string(mocker, tmp_path, tool, content, expected_include):
    """String include from TOML should be normalized to list."""
    toml_file = tmp_path / "foo.toml"
    toml_file.write_text(content)

    cli_config = {"config_file": str(toml_file), "include": None}
    parser = mocker.Mock()
    parser.parse_args().__dict__ = cli_config

    result = get_config(parser, argv=[], defaults={}, tool=tool)
    assert result["include"] == expected_include


def test_get_config_normalizes_both_patterns(mocker, tmp_path):
    """get_config should normalize both exclude and include from TOML files."""
    toml_file = tmp_path / "foo.toml"
    toml_file.write_text('[tool.diff_cover]\nexclude="*.pyc"\ninclude="src/**"')

    cli_config = {"config_file": str(toml_file), "exclude": None, "include": None}
    parser = mocker.Mock()
    parser.parse_args().__dict__ = cli_config

    result = get_config(parser, argv=[], defaults={}, tool=Tool.DIFF_COVER)

    assert result["exclude"] == ["*.pyc"]
    assert result["include"] == ["src/**"]
