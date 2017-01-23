Connexions EPUB3 Library
========================

Library for parsing and building EPUB3 files for connexions content.

Getting started
---------------

To install::

    python setup.py install

Running tests
-------------

.. image:: https://travis-ci.org/Connexions/cnx-epub.png?branch=master
   :target: https://travis-ci.org/Connexions/cnx-epub

.. image:: https://codecov.io/gh/Connexions/cnx-epub/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Connexions/cnx-epub
  
Either of the following will work::

    $ python -m unittest discover
    $ python setup.py test

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
