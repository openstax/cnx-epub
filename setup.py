# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


IS_PY3 = sys.version_info > (3,)


install_requires = [
    'jinja2',
    'lxml',
    ]
tests_require = [
    ]
extras_require = {
    'test': tests_require,
    }
description = "Library for building and paring Connexions' EPUBs."

if not IS_PY3:
    tests_require.append('mock')


setup(
    name='cnx-epub',
    version='0.8.0',
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-epub",
    license='AGPL, See also LICENSE.txt',
    description=description,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    packages=find_packages(),
    include_package_data=False,
    entry_points={
        'console_scripts': [
            'cnx-epub-single_html = cnxepub.scripts.single_html.main:main',
            ],
        },
    test_suite='cnxepub.tests',
    zip_safe=False,
    )
