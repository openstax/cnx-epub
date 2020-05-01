# -*- coding: utf-8 -*-
import sys
import versioneer
from setuptools import setup, find_packages


IS_PY3 = sys.version_info > (3,)


install_requires = [
    'jinja2',
    'lxml',
    'requests',
    'python-memcached'
    ] if IS_PY3 else [
    'jinja2==2.11.2',
    'MarkupSafe==1.1.1',
    'lxml',
    'requests',
    'python-memcached'
    ]
collation_requires = [
    'cnx-easybake',
    ]
tests_require = [
    ]
tests_require.extend(collation_requires)
extras_require = {
    'collation': collation_requires,
    'test': tests_require,
    }
description = "Library for building and paring Connexions' EPUBs."

if not IS_PY3:
    tests_require.append('mock')

console_scripts = [
    'cnx-epub-single_html = cnxepub.scripts.single_html.main:main',
    ('cnx-epub-validate-collated = '
     'cnxepub.scripts.collated_single_html.main:main'),
]

setup(
    name='cnx-epub',
    version=versioneer.get_version(),
    author='Connexions team',
    author_email='info@cnx.org',
    url="https://github.com/connexions/cnx-epub",
    license='AGPL, See also LICENSE.txt',
    description=description,
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require=extras_require,
    packages=find_packages(),
    include_package_data=True,
    cmdclass=versioneer.get_cmdclass(),
    entry_points={
        'console_scripts': console_scripts,
        },
    test_suite='cnxepub.tests',
    zip_safe=False,
    dependency_links=[
        'git+https://github.com/Connexions/cnx-easybake.git#egg=cnx-easybake']
    )
