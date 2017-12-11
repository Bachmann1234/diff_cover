diff-cover |build-status| |coverage-status| |docs-status|
=========================================================

Automatically find diff lines that need test coverage.
Also finds diff lines that have violations (according to tools such as pycodestyle,
pyflakes, flake8, or pylint).
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
- Clover__ (Java)
- coverage.py__ (Python)
- JSCover__ (JavaScript)

__ http://cobertura.sourceforge.net/
__ http://openclover.org/
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

    git clone https://github.com/Bachmann1234/diff-cover.git
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

Where ``tool`` is the quality checker to use. Currently ``pycodestyle``, ``pyflakes``,
``flake8``, ``pylint``, ``checkstyle``, ``checkstylexml`` are supported, but more
checkers can (and should!) be integrated. There's no way to run ``findbugs`` from
``diff-quality`` as it operating over the generated java bytecode and should be
integrated into the build framework.

Like ``diff-cover``, HTML reports can be generated with

.. code:: bash

    diff-quality --violations=<tool> --html-report report.html

If you have already generated a report using ``pycodestyle``, ``pyflakes``, ``flake8``,
``pylint``, ``checkstyle``, ``checkstylexml``, or ``findbugs`` you can pass the report
to ``diff-quality``.  This is more efficient than letting ``diff-quality`` re-run
``pycodestyle``, ``pyflakes``, ``flake8``, ``pylint``, ``checkstyle``, or ``checkstylexml``.

.. code:: bash

    # For pylint < 1.0
    pylint -f parseable > pylint_report.txt

    # For pylint >= 1.0
    pylint --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" > pylint_report.txt

    # Use the generated pylint report when running diff-quality
    diff-quality --violations=pylint pylint_report.txt

    # Use a generated pycodestyle report when running diff-quality.
    pycodestyle > pycodestyle_report.txt
    diff-quality --violations=pycodestyle pycodestyle_report.txt

Note that you must use the ``-f parseable`` option to generate
the ``pylint`` report for pylint versions less than 1.0 and the
``--msg-template`` option for versions >= 1.0.

``diff-quality`` will also accept multiple ``pycodestyle``, ``pyflakes``, ``flake8``,
or ``pylint`` reports:

.. code:: bash

    diff-quality --violations=pylint report_1.txt report_2.txt

If you need to pass in additional options you can with the ``options`` flag

.. code:: bash

    diff-quality --violations=pycodestyle --options="--exclude='*/migrations*' --statistics" pycodestyle_report.txt

Compare Branch
--------------

By default, ``diff-cover`` compares the current branch to ``origin/master``.  To specify a different compare branch:

.. code:: bash

    diff-cover coverage.xml --compare-branch=origin/release

Fail Under
----------

To have ``diff-cover`` and ``diff-quality`` return a non zero status code if the report quality/coverage percentage is
below a certain threshold specify the fail-under parameter

.. code:: bash

    diff-cover coverage.xml --fail-under=80
    diff-quality --violations=pycodestyle --fail-under=80

The above will return a non zero status if the coverage or quality score was below 80%

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

**Solution**: Your project needs a `pylintrc` file. Provide this file (it can be empty) and ``diff-quality`` should run without issue.

**Issue**: ``diff-quality`` reports "Quality tool not installed"

**Solution**: ``diff-quality`` assumes you have the tool you wish to run against your diff installed. If you do not have it
then install it with your favorite package manager.

License
-------

The code in this repository is licensed under the Apache 2.0 license.
Please see ``LICENSE.txt`` for details.


How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.

Setting Up For Development
~~~~~~~~~~~~~~~~~~~~~~~~~~

diff-cover is written to support many versions of python. The best way to set
your machine up for development is to make sure you have ``tox`` installed which
can be installed using ``pip``.

.. code:: bash

    pip install tox

Now by simply running ``tox`` from the project root you will have environments
for all the supported python versions. These will be in the ``.tox`` directory.

To create a specific python dev environment just make a virtualenv for your python
version and then install the appropriate test-requirements file.

For example, setting up python 3:

.. code:: bash

    pyvenv venv
    source venv/bin/activate
    pip install -r test-requirements.txt


Special Thanks
-------------------------

Shout out to the original author of diff-cover `Will Daly 
<https://github.com/wedaly>`_ and the original author of diff-quality `Sarina Canelake 
<https://github.com/sarina>`_. 

Originally created with the support of `edX 
<https://github.com/edx>`_.


.. |build-status| image:: https://travis-ci.org/Bachmann1234/diff-cover.png
    :target: https://travis-ci.org/Bachmann1234/diff-cover
    :alt: Build Status
.. |coverage-status| image:: https://coveralls.io/repos/Bachmann1234/diff-cover/badge.png
    :target: https://coveralls.io/r/Bachmann1234/diff-cover
    :alt: Coverage Status
.. |docs-status| image:: https://readthedocs.org/projects/diff-cover/badge/
    :alt: Documentation Status
    :scale: 100%
    :target: http://diff-cover.readthedocs.org/en/latest/
