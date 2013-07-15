diff-cover
==========

Automatically find diff lines that need test coverage.
Also finds diff lines that have violations (according to tools such as pep8 or pylint).
This is used as a code quality metric during code reviews.

Overview
--------

Diff coverage is the percentage of new or modified 
lines that are covered by tests.  This provides a clear 
and achievable standard for code review: If you touch a line 
of code, that line should be covered.  Code coverage
is *every* developer's responsibility!

The ``diff-cover`` command line tool compares an XML coverage report
with the output of ``git diff``.  It then reports coverage information
for lines in the diff.

Currently, ``diff-cover`` requires that:

- You are using ``git`` for version control.
- Your test runner generates coverage reports in Cobertura XML format.

Cobertura XML coverage reports can be generated with many coverage tools,
including:

- Cobertura__ (Java)
- coverage.py__ (Python)
- JSCover__ (JavaScript)

__ http://cobertura.sourceforge.net/
__ http://nedbatchelder.com/code/coverage/
__ http://tntim96.github.io/JSCover/


``diff-cover`` is designed to be extended.  If you are interested
in adding support for other version control systems or coverage
report formats, see below for information on how to contribute!


Installation
------------

To install the latest release:

.. code:: bash

    pip install diff_cover


To install the development version:

.. code:: bash

    git clone https://github.com/edx/diff-cover.git
    cd diff-cover
    python setup.py install


Getting Started
---------------

1. Set the current working directory to a ``git`` repository.
   
2. Run your test suite under coverage and generate a Cobertura XML report.
   For example, if you are using `nosetests`__ and `coverage.py`__:

.. code:: bash

    nosetests --with-coverage
    coverage xml

__ http://nose.readthedocs.org
__ http://nedbatchelder.com/code/coverage/

This will create a ``coverage.xml`` file in the current working directory.

**NOTE**: If you are using a different coverage generator, you will
need to use different commands to generate the coverage XML report.


3. Run ``diff-cover``:

.. code:: bash

    diff-cover coverage.xml

This will compare the current ``git`` branch to ``origin/master`` and print
the diff coverage report to the console.

You can also generate an HTML version of the report:

.. code:: bash

	diff-cover coverage.xml --html-report report.html

Multiple XML Coverage Reports
-------------------------------

In the case that one has multiple xml reports form multiple test suites, you 
can get a combined coverage report (a line is counted  as covered if it is 
covered in ANY of the xml reports) by running ``diff-cover`` with multiple 
coverage reports as arguments. You may specify any arbitrary number of coverage 
reports:

.. code:: bash

	diff-cover coverage1.xml coverage2.xml 

Quality Coverage
-----------------
You can use diff-cover to see quality reports on the diff as well by running
``diff-quality``.

.. code :: bash

    diff-quality --violations=<tool>

Where ``tool`` is the quality checker to use. Currently ``pylint`` and
``pep8`` are supported, but more checkers can (and should!) be integrated.

Like ``diff-cover``, HTML reports can be generated with

.. code:: bash

    diff-quality --violations=<tool> --html-report report.html

Troubleshooting
----------------------

**Issue**: ``diff-cover`` always reports: "No lines with coverage information in this diff."

**Solution**: ``diff-cover`` matches source files in the coverage XML report with
source files in the ``git diff``.  For this reason, it's important
that the relative paths to the files match.  If you are using `coverage.py`__
to generate the coverage XML report, then make sure you run
``diff-cover`` from the same working directory.

__ http://nedbatchelder.com/code/coverage/

**Issue**: ``GitDiffTool._execute()`` raises the error: 

.. code:: bash

    fatal: ambiguous argument 'origin/master...HEAD': unknown revision or path not in the working tree.

This is known to occur when running ``diff-cover`` in `Travis CI`__

__ http://travis-ci.org

**Solution**: Fetch the remote master branch before running ``diff-cover``:

.. code:: bash

    git fetch origin master:refs/remotes/origin/master

**Issue**: ``diff-quality`` reports "diff_cover.violations_reporter.QualityReporterError: No config file found, using default configuration"

**Solution**: Your project needs a `pylintrc` file. Provide this file (it can be empty) and ``diff-quality`` should run wihtout issue.

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


Mailing List and IRC Channel
----------------------------

You can discuss this code on the `edx-code Google Group`__ or in the
``edx-code`` IRC channel on Freenode.

__ https://groups.google.com/forum/#!forum/edx-code
