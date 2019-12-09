from __future__ import unicode_literals

import pluggy

VERSION = '2.4.1'
DESCRIPTION = 'Automatically find diff lines that need test coverage.'
QUALITY_DESCRIPTION = 'Automatically find diff lines with quality violations.'

# Other packages that implement diff_cover plugins use this.
hookimpl = pluggy.HookimplMarker('diff_cover')
