# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


IS_PY3 = sys.version_info > (3,)


install_requires = [
    'lxml',
    ]
tests_require = [
    ]
extras_require = {
    'test': tests_require,
    }
description = "Library for building and paring Connexions' EPUBs."

if IS_PY3:
    tests_require.append('mock')


setup(
    name='cnx-epub',
    version='0.1',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-epub",
    license='LGPL, See also LICENSE.txt',
    description=description,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    packages=find_packages(),
    include_package_data=False,
    entry_points="""\
    [console_scripts]
    """,
    zip_safe=False,
    )
