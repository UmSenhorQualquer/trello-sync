#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, os
from setuptools import setup, find_packages

with open(os.path.join('README.md'), 'r') as fd:
    long_description = fd.read()

setup(
    name='Trello sync',
    version="0",
    description="Sync teams trello boards",
    author=['Ricardo Ribeiro'],
    author_email='ricardojvr@gmail.com',
    include_package_data=True,
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    packages = find_packages(),
    install_requires = [
        'parse',
        'django',
        'pyforms-web'
    ]
)
