#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
import sys
from io import open
from setuptools import setup, find_packages


version = '1.9.3'

def read_md(file_path):
    with open(file_path) as fp:
        return fp.read()


if sys.argv[-1] == 'publish':        
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'version %s'" % (version, version))
    print("  git push --tags")
    sys.exit()

setup(
    name = 'django-subadmin',
    version = version,
    install_requires = (),
    author = 'Mitja Pagon',
    author_email = 'mitja@inueni.com',
    license = 'MIT',
    url = 'https://github.com/inueni/django-subadmin/',
    keywords = 'django admin modeladmin foreignkey related field',
    description = 'A special kind of ModelAdmin that allows it to be nested within another ModelAdmin',
    long_description = read_md('README.md'),
    long_description_content_type = 'text/markdown',
    packages = find_packages(),
    python_requires = '>2.6, <3.0',
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
    ]
)
