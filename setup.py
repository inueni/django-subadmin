#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from setuptools import setup, find_packages
import os
import sys

version = '1.9.0'

try:
    from pypandoc import convert
    def read_md(f):
        return convert(f, 'rst')
except ImportError:
    print("warning: pypandoc module not found, could not convert Markdown to RST")
    def read_md(f):
        return open(f, 'r', encoding='utf-8').read()


if sys.argv[-1] == 'publish':
    try:
        import pypandoc
    except ImportError:
        print("pypandoc not installed.\nUse `pip install pypandoc`.")
        
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
    packages = find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
    ]
)