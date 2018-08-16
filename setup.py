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
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


version = get_version('fhirpy')


with open('README.md') as f:
    long_description = f.read()


setup(
    name='fhirpy',
    version=version,
    url='http://github.com/beda-software/fhir-py',
    license='',
    description='FHIR client for python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='fhir',
    author='beda.software',
    author_email='fhirpy@beda.software',
    packages=['fhirpy'],
    include_package_data=True,
    install_requires=['requests'],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
