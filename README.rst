diff-cover |pypi-version| |conda-version| |build-status|
========================================================================================

Automatically find diff lines that need test coverage.
Also finds diff lines that have violations (according to tools such
as pycodestyle, pyflakes, flake8, or pylint).
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
- Your test runner generates coverage reports in Cobertura, Clover
  or JaCoCo XML format, or LCov format.

Supported XML or LCov coverage reports can be generated with many coverage tools,
including:

- Cobertura__ (Java)
- Clover__ (Java)
- JaCoCo__ (Java)
- coverage.py__ (Python)
- JSCover__ (JavaScript)
- lcov__ (C/C++)

__ http://cobertura.sourceforge.net/
__ http://openclover.org/
__ https://www.jacoco.org/
__ http://nedbatchelder.com/code/coverage/
__ http://tntim96.github.io/JSCover/
__ https://ltp.sourceforge.net/coverage/lcov.php


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
    poetry install
    poetry shell


Getting Started
---------------

1. Set the current working directory to a ``git`` repository.

2. Run your test suite under coverage and generate a [Cobertura, Clover or JaCoCo] XML report.
   For example, using `pytest-cov`__:

.. code:: bash

    pytest --cov --cov-report=xml

__ https://pypi.org/project/pytest-cov

This will create a ``coverage.xml`` file in the current working directory.

**NOTE**: If you are using a different coverage generator, you will
need to use different commands to generate the coverage XML report.


3. Run ``diff-cover``:

.. code:: bash

    diff-cover coverage.xml

This will compare the current ``git`` branch to ``origin/main`` and print
the diff coverage report to the console.

You can also generate an HTML, JSON or Markdown version of the report:

.. code:: bash

    diff-cover coverage.xml --html-report report.html
    diff-cover coverage.xml --json-report report.json
    diff-cover coverage.xml --markdown-report report.md

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
checkers can (and should!) be supported. See the section "Adding `diff-quality``
Support for a New Quality Checker".

NOTE: There's no way to run ``findbugs`` from ``diff-quality`` as it operating
over the generated java bytecode and should be integrated into the build
framework.

Like ``diff-cover``, HTML, JSON or Markdown reports can be generated with

.. code:: bash

    diff-quality --violations=<tool> --html-report report.html
    diff-quality --violations=<tool> --json-report report.json
    diff-quality --violations=<tool> --markdown-report report.md

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

By default, ``diff-cover`` compares the current branch to ``origin/main``.  To specify a different compare branch:

.. code:: bash

    diff-cover coverage.xml --compare-branch=origin/release

Fail Under
----------

To have ``diff-cover`` and ``diff-quality`` return a non zero status code if the report quality/coverage percentage is
below a certain threshold specify the fail-under parameter

.. code:: bash

    diff-cover coverage.xml --fail-under=80
    diff-quality --violations=pycodestyle --fail-under=80

The above will return a non zero status if the coverage or quality score was below 80%.

Exclude/Include paths
---------------------

Explicit exclusion of paths is possible for both ``diff-cover`` and ``diff-quality``, while inclusion is
only supported for ``diff-quality`` (since 5.1.0).

The exclude option works with ``fnmatch``, include with ``glob``. Both options can consume multiple values.
Include options should be wrapped in double quotes to prevent shell globbing. Also they should be relative to
the current git directory.

.. code:: bash

    diff-cover coverage.xml --exclude setup.py
    diff-quality --violations=pycodestyle --exclude setup.py

    diff-quality --violations=pycodestyle --include project/foo/**

The following is executed for every changed file:

#. check if any include pattern was specified
#. if yes, check if the changed file is part of at least one include pattern
#. check if the file is part of any exclude pattern

Ignore/Include based on file status in git
------------------------------------------
Both ``diff-cover`` and ``diff-quality`` allow users to ignore and include files based on the git
status: staged, unstaged, untracked:

* ``--ignore-staged``: ignore all staged files (by default include them)
* ``--ignore-unstaged``: ignore all unstaged files (by default include them)
* ``--include-untracked``: include all untracked files (by default ignore them)

Quiet mode
----------
Both ``diff-cover`` and ``diff-quality`` support a quiet mode which is disable by default.
It can be enabled by using the ``-q``/``--quiet`` flag:

.. code:: bash

    diff-cover coverage.xml -q
    diff-quality --violations=pycodestyle -q

If enabled, the tool will only print errors and failures but no information or warning messages.

Configuration files
-------------------
Both tools allow users to specify the options in a configuration file with `--config-file`/`-c`:

.. code:: bash

    diff-cover coverage.xml --config-file myconfig.toml
    diff-quality --violations=pycodestyle --config-file myconfig.toml

Currently, only TOML files are supported.
Please note, that only non-mandatory options are supported.
If an option is specified in the configuration file and over the command line, the value of the
command line is used.

TOML configuration
~~~~~~~~~~~~~~~~~~

The parser will only react to configuration files ending with `.toml`.
To use it, install `diff-cover` with the extra requirement `toml`.

The option names are the same as on the command line, but all dashes should be underscores.
If an option can be specified multiple times, the configuration value should be specified as a list.

.. code:: toml

    [tool.diff_cover]
    compare_branch = "origin/feature"
    quiet = true

    [tool.diff_quality]
    compare_branch = "origin/feature"
    ignore_staged = true


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

    fatal: ambiguous argument 'origin/main...HEAD': unknown revision or path not in the working tree.

This is known to occur when running ``diff-cover`` in `Travis CI`__

__ http://travis-ci.org

**Solution**: Fetch the remote main branch before running ``diff-cover``:

.. code:: bash

    git fetch origin master:refs/remotes/origin/main

**Issue**: ``diff-quality`` reports "diff_cover.violations_reporter.QualityReporterError:
No config file found, using default configuration"

**Solution**: Your project needs a `pylintrc` file.
Provide this file (it can be empty) and ``diff-quality`` should run without issue.

**Issue**: ``diff-quality`` reports "Quality tool not installed"

**Solution**: ``diff-quality`` assumes you have the tool you wish to run against your diff installed.
If you do not have it then install it with your favorite package manager.

**Issue**: ``diff-quality`` reports no quality issues

**Solution**: You might use a pattern like ``diff-quality --violations foo *.py``. The last argument
is not used to specify the files but for the quality tool report. Remove it to resolve the issue

License
-------

The code in this repository is licensed under the Apache 2.0 license.
Please see ``LICENSE.txt`` for details.


How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork.

NOTE: ``diff-quality`` supports a plugin model, so new tools can be integrated
without requiring changes to this repo. See the section "Adding `diff-quality``
Support for a New Quality Checker".

Setting Up For Development
~~~~~~~~~~~~~~~~~~~~~~~~~~

This project is managed with `poetry` this can be installed with `pip`
poetry manages a python virtual environment and organizes dependencies. It also
packages this project.

.. code:: bash

    pip install poetry

.. code:: bash

    poetry install

I would also suggest running this command after. This will make it so git blame ignores the commit
that formatted the entire codebase.

.. code:: bash

    git config blame.ignoreRevsFile .git-blame-ignore-revs


Adding `diff-quality`` Support for a New Quality Checker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Adding support for a new quality checker is simple. ``diff-quality`` supports
plugins using the popular Python
`pluggy package <https://pluggy.readthedocs.io/en/latest/>`_.

If the quality checker is already implemented as a Python package, great! If not,
`create a Python package <https://packaging.python.org/tutorials/packaging-projects/>`_
to host the plugin implementation.

In the Python package's ``setup.py`` file, define an entry point for the plugin,
e.g.

.. code:: python

    setup(
        ...
        entry_points={
            'diff_cover': [
                'sqlfluff = sqlfluff.diff_quality_plugin'
            ],
        },
        ...
    )

Notes:

* The dictionary key for the entry point must be named ``diff_cover``
* The value must be in the format ``TOOL_NAME = YOUR_PACKAGE.PLUGIN_MODULE``

When your package is installed, ``diff-quality`` uses this information to
look up the tool package and module based on the tool name provided to the
``--violations`` option of the ``diff-quality`` command, e.g.:

.. code:: bash

    $ diff-quality --violations sqlfluff

The plugin implementation will look something like the example below. This is
a simplified example based on a working plugin implementation.

.. code:: python

    from diff_cover.hook import hookimpl as diff_cover_hookimpl
    from diff_cover.violationsreporters.base import BaseViolationReporter, Violation

    class SQLFluffViolationReporter(BaseViolationReporter):
        supported_extensions = ['sql']

        def __init__(self):
            super(SQLFluffViolationReporter, self).__init__('sqlfluff')

        def violations(self, src_path):
            return [
                Violation(violation.line_number, violation.description)
                for violation in get_linter().get_violations(src_path)
            ]

        def measured_lines(self, src_path):
            return None

        @staticmethod
        def installed():
            return True


    @diff_cover_hookimpl
    def diff_cover_report_quality():
        return SQLFluffViolationReporter()

Important notes:

* ``diff-quality`` is looking for a plugin function:

  * Located in your package's module that was listed in the ``setup.py`` entry point.
  * Marked with the ``@diff_cover_hookimpl`` decorator
  * Named ``diff_cover_report_quality``. (This distinguishes it from any other
    plugin types ``diff_cover`` may support.)
* The function should return an object with the following properties and methods:

  * ``supported_extensions`` property with a list of supported file extensions
  * ``violations()`` function that returns a list of ``Violation`` objects for
    the specified ``src_path``. For more details on this function and other
    possible reporting-related methods, see the ``BaseViolationReporter`` class
    `here <https://github.com/Bachmann1234/diff_cover/blob/main/diff_cover/violationsreporters/base.py>`_.

Special Thanks
-------------------------

Shout out to the original author of diff-cover `Will Daly
<https://github.com/wedaly>`_ and the original author of diff-quality `Sarina Canelake
<https://github.com/sarina>`_.

Originally created with the support of `edX
<https://github.com/edx>`_.


.. |pypi-version| image:: https://img.shields.io/pypi/v/diff-cover.svg
    :target: https://pypi.org/project/diff-cover
    :alt: PyPI version
.. |conda-version| image:: https://img.shields.io/conda/vn/conda-forge/diff-cover.svg
    :target: https://anaconda.org/conda-forge/diff-cover
    :alt: Conda version
.. |build-status| image:: https://github.com/bachmann1234/diff_cover/actions/workflows/verify.yaml/badge.svg?branch=main
    :target: https://github.com/Bachmann1234/diff_cover/actions/workflows/verify.yaml
    :alt: Build Status
