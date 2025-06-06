import argparse

import pytest

from diff_cover import config_parser
from diff_cover.config_parser import (
    ParserError,
    TOMLParser,
    Tool,
    get_config,
    get_parser,
)

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
        get_config(parser, argv=[], tool=tool)


@pytest.mark.parametrize(
    "tool,argv,file_content,expected",
    [
        (
            Tool.DIFF_COVER,
            ["-aa", "2"],
            None,
            {"aa": 2, "bb": None, "cc": None},
        ),
        (
            Tool.DIFF_QUALITY,
            ["-aa", "3"],
            None,
            {"aa": 3, "bb": None, "cc": None},
        ),
        (
            Tool.DIFF_COVER,
            ["-aa", "2", "-cc", "1"],
            "[tool.diff_cover]\naa=1\nbb=6",
            {"aa": 2, "bb": 6, "cc": 1},
        ),
    ],
)
def test_get_config(tmp_path, tool, argv, file_content, expected):
    if file_content:
        toml_file = tmp_path / "foo.toml"
        toml_file.write_text(file_content)
        argv.extend(["--config-file", str(toml_file)])

    parser = get_parser(description="test")
    parser.add_argument("-aa", type=int, default=0)
    parser.add_argument("-bb", type=int, default=0)
    parser.add_argument("-cc", type=int, default=0)
    actual = get_config(parser, argv=argv, tool=tool)
    actual.pop("config_file")
    assert actual == expected
