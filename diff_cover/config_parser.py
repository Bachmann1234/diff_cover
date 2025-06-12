import abc
import enum

import configargparse

CONFIG_FILE_HELP = "The configuration file to use"


class Tool(enum.Enum):
    DIFF_COVER = enum.auto()
    DIFF_QUALITY = enum.auto()


def get_parser(description):
    sections = ["tool.diff_cover", "tool:diff_cover", "diff_cover"]
    parser = configargparse.ArgParser(
        description=description,
        default_config_files=["pyproject.toml"],
        config_file_parser_class=configargparse.CompositeConfigParser(
            [
                configargparse.TomlConfigParser(sections),
            ]
        ),
    )
    parser.add_argument(
        "-c",
        "--config-file",
        help=CONFIG_FILE_HELP,
        is_config_file=True,
        metavar="CONFIG_FILE",
    )
    return parser


def get_config(parser, argv, tool):
    import ipdb; ipdb.set_trace()
    cli_config = vars(parser.parse_args(argv))
    # if cli_config["config_file"]:
    #     file_config = _parse_config_file(cli_config["config_file"], tool)
    # else:
    file_config = {}

    config = {}
    for config_dict in [file_config, cli_config]:
        for key, value in config_dict.items():
            config[key] = value

    return config
