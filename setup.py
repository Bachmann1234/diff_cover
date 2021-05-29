#!/usr/bin/env python

from setuptools import setup
from diff_cover import VERSION, DESCRIPTION

REQUIREMENTS = [line.strip() for line in open("requirements.txt").readlines()]
setup(
    name="diff_cover",
    version=VERSION,
    author="Matt Bachmann",
    url="https://github.com/Bachmann1234/diff-cover",
    test_suite="nose.collector",
    description=DESCRIPTION,
    license="Apache 2.0",
    python_requires=">= 3.6",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
    ],
    packages=["diff_cover", "diff_cover/violationsreporters"],
    package_data={
        "diff_cover": [
            "templates/*.txt",
            "templates/*.html",
            "templates/*.css",
            "templates/*.md",
        ]
    },
    install_requires=REQUIREMENTS,
    entry_points={
        "console_scripts": [
            "diff-cover = diff_cover.diff_cover_tool:main",
            "diff-quality = diff_cover.diff_quality_tool:main",
        ]
    },
)
