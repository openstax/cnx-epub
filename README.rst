Connexions EPUB3 Library
========================

Library for parsing and building EPUB3 files for connexions content.

Getting started
---------------

Prerequisites needed e.g. on Ubuntu Linux ``sudo apt install build-essential python-dev python3-dev libicu-dev``

To install::

    pip install lxml==3.6.4
    pip install git+https://github.com/openstax/cnx-cssselect2.git#egg=cnx-cssselect2
    pip install git+https://github.com/Connexions/cnx-easybake.git#egg=cnx-easybake
    python setup.py install

Running tests
-------------

.. image:: https://codecov.io/gh/openstax/cnx-epub/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/openstax/cnx-epub
  
Either of the following will work::

    python setup.py test
    python -m unittest discover

Format notes
------------

Order of documents
~~~~~~~~~~~~~~~~~~

To enforcing order of contents, we use the navigation document rather than
the Open Packaging Format (OPF),
which supports a ``spine`` element that aids in epub reader in navigation order.
The Connexions library does not use the spine for order.
A navigation document is the authority on order of contents
and which contents are document like.
Anything not included in the navigation document is considered a resource.

Document encapsulation
~~~~~~~~~~~~~~~~~~~~~~

Collections are easy because they will be sent across as individual OPF entries
that contain the collection tree as navigation documents.
In the case of publishing module documents without a collection,
the navigation document will be flagged as a non-document item.

License
-------

This software is subject to the provisions of the GNU Affero General
Public License Version 3.0 (AGPL). See license.txt for details.
Copyright (c) 2013 Rice University
