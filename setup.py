#!/usr/bin/env python

import os
from setuptools import setup
from diff_cover import VERSION, DESCRIPTION

REQUIREMENTS = [line.strip() for line in
                open(os.path.join("requirements", "requirements.txt")).readlines()]
setup(
    name='diff_cover',
    version=VERSION,
    author='Matt Bachmann',
    url='https://github.com/Bachmann1234/diff-cover',
    description=DESCRIPTION,
    license='Apache 2.0',
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Environment :: Console',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: Apache Software License',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 "Programming Language :: Python :: 3",
                 'Topic :: Software Development :: Testing',
                 'Topic :: Software Development :: Quality Assurance'],
    packages=['diff_cover', 'diff_cover/violationsreporters'],
    package_data={'diff_cover': ['templates/*.txt', 'templates/*.html', 'templates/*.css']},
    install_requires=REQUIREMENTS,
    entry_points={
        'console_scripts': ['diff-cover = diff_cover.tool:main',
                            'diff-quality = diff_cover.tool:main']
    }
)
