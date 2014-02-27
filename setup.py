# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


install_requires = (
    'lxml',
    )
description = "Library for building and paring Connexions' EPUBs."


setup(
    name='cnx-epub',
    version='0.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-epub",
    license='LGPL, See also LICENSE.txt',
    description=description,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=False,
    entry_points="""\
    [console_scripts]
    """,
    )
