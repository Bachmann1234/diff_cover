#!/usr/bin/env python

from setuptools import setup

setup(
    name='diff_cover',
    version=0.1,
    description='Automatically find diff lines that need test coverage.',
    author='Will Daly',
    author_email='will@edx.org',
    packages=['diff_cover'],
    install_requires=['setuptools'],
    entry_points={
        'console_scripts': ['diff-cover = diff_cover.tool:main']
    }
)
