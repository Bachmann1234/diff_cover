import pluggy

hookspec = pluggy.HookspecMarker("diff_cover")


@hookspec
def diff_cover_report_quality(reports, options):  # pylint: disable=unused-argument
    """
    Return a 2-part tuple:
    - Quality plugin name
    - Object that implements the BaseViolationReporter protocol

    ``reports`` is the list of open pre-generated report file handles and
    ``options`` the user options string; both are passed by ``diff-quality``.
    A plugin may declare either or neither argument.
    """
