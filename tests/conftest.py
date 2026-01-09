import pytest

from diff_cover.git_path import GitPathTool


@pytest.fixture(autouse=True)
def reset_git_path_tool():
    """Reset GitPathTool before each test to ensure test isolation.

    GitPathTool uses class variables (_cwd and _root) that persist across tests.
    This fixture ensures each test starts with a clean state.
    """
    GitPathTool._cwd = None
    GitPathTool._root = None
    yield
    GitPathTool._cwd = None
    GitPathTool._root = None
