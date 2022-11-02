# -*- coding: utf-8 -*-
import sys
import versioneer
from setuptools import setup, find_packages


install_requires = [
    'jinja2',
    'lxml==4.9.1',  # Unicode problem in lxml 4.5.0 cnx#924
    'requests',
    'PyICU==2.10.1',
    ]
description = "Library for building and paring Connexions' EPUBs."

setup(
    name='cnx-epub',
    version=versioneer.get_version(),
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-epub",
    license='AGPL, See also LICENSE.txt',
    description=description,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=True,
    cmdclass=versioneer.get_cmdclass(),
    test_suite='cnxepub.tests',
    zip_safe=False,
    )
