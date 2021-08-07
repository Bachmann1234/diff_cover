import pkg_resources

VERSION = pkg_resources.get_distribution("diff_cover").version
DESCRIPTION = "Automatically find diff lines that need test coverage."
QUALITY_DESCRIPTION = "Automatically find diff lines with quality violations."
