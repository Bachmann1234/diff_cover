diff-cover
==========

Automatically find diff lines that need test coverage.  
This is used as a code quality metric during code reviews.

Overview
--------

``diff-cover`` compares an XML coverage report with a ``git diff``
and reports which lines in the diff are covered.

XML coverage reports can be generated with tools such as 
`coverage.py`__

__ <http://nedbatchelder.com/code/coverage/>


Getting Started
---------------

To install, navigate to the ``diff-cover`` directory and run:

    python setup.py install

You can then use the command:

    diff-cover COVERAGE_XML --git-branch BRANCH [--html-report REPORT.html]

This will compare the current git branch to ``BRANCH``, identify lines
that are not covered (based on ``COVERAGE_XML``), and (optionally) generate an HTML report.

``diff-cover`` ignores files not referenced in ``COVERAGE_XML``, since these files
are not tested.  This means that documentation and configuration changes
will be ignored.

If ``--html-report`` is not specified, ``diff-cover`` prints a text report
to stdout.


License
-------

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.


How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.


Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org

Please see http://code.edx.org/security/ for details.


Mailing List and IRC Channel
----------------------------

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
