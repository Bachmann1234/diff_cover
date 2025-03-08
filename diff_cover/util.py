import os.path
import posixpath


def to_unix_path(path):
    """
    Tries to ensure tha the path is a normalized unix path.
    This seems to be the solution cobertura used....
    https://github.com/cobertura/cobertura/blob/642a46eb17e14f51272c6962e64e56e0960918af/cobertura/src/main/java/net/sourceforge/cobertura/instrument/ClassPattern.java#L84

    I know of at least one case where this will fail (\\) is allowed in unix paths.
    But I am taking the bet that this is not common. We deal with source code.

    :param path: string of the path to convert
    :return: the unix version of that path
    """
    return posixpath.normpath(os.path.normcase(path).replace("\\", "/"))


def to_unescaped_filename(filename: str) -> str:
    """Try to unescape the given filename.

    Some filenames given by git might be escaped with C-style escape sequences
    and surrounded by double quotes.
    """
    if not (filename.startswith('"') and filename.endswith('"')):
        return filename

    # Remove surrounding quotes
    unquoted = filename[1:-1]

    # Handle C-style escape sequences
    result = []
    i = 0
    while i < len(unquoted):
        if unquoted[i] == "\\" and i + 1 < len(unquoted):
            # Handle common C escape sequences
            next_char = unquoted[i + 1]
            result.append(
                {
                    "\\": "\\",
                    '"': '"',
                    "a": "a",
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "b": "\b",
                    "f": "\f",
                }.get(next_char, next_char)
            )
            i += 2
        else:
            result.append(unquoted[i])
            i += 1

    return "".join(result)
