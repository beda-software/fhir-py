#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
from io import open

from setuptools import setup


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


version = get_version("fhirpy")

with open("README.md") as f:
    long_description = f.read()

setup(
    name="fhirpy",
    version=version,
    url="http://github.com/beda-software/fhir-py",
    license="",
    description="FHIR client for python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="fhir",
    author="beda.software",
    author_email="fhirpy@beda.software",
    packages=["fhirpy"],
    include_package_data=True,
    install_requires=["requests>=2.25.1", "aiohttp>=3.6.3", "pytz"],
    tests_require=["pytest>=6.2.4", "pytest-asyncio>=0.15.1", "responses>=0.13.3"],
    zip_safe=False,
    project_urls={
        "Source Code": "https://github.com/beda-software/fhir-py",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
