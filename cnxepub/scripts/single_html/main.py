# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import print_function

import argparse
import logging
import os
import sys

from lxml import etree
import cnxepub


ARCHIVEHTML = 'https://archive.cnx.org/contents/{}.html'
MATHJAX_URL = 'https://cdn.mathjax.org/mathjax/{mathjax_version}/'\
              'unpacked/MathJax.js?config=MML_HTMLorMML'


parts = ['page', 'chapter', 'unit', 'book', 'series']
partcount = {}
logger = logging.getLogger('single_html')


def single_html(epub_file_path, html_out=sys.stdout, mathjax_version=None,
                numchapters=None):
    """Generate complete book HTML."""
    epub = cnxepub.EPUB.from_file(epub_file_path)
    if len(epub) != 1:
        raise Exception('Expecting an epub with one book')

    package = epub[0]
    binder = cnxepub.adapt_package(package)
    partcount.update({}.fromkeys(parts, 0))
    partcount['book'] += 1

    html = cnxepub.SingleHTMLFormatter(binder)

    # Truncate binder to the first N chapters where N = numchapters.
    logger.debug('Full binder: {}'.format(cnxepub.model_to_tree(binder)))
    if numchapters is not None:
        apply_numchapters(html.get_node_type, binder, numchapters)
        logger.debug('Truncated Binder: {}'.format(
            cnxepub.model_to_tree(binder)))

    # Add mathjax to the page.
    if mathjax_version:
        etree.SubElement(
            html.head,
            'script',
            src=MATHJAX_URL.format(mathjax_version=mathjax_version))

    print(str(html), file=html_out)
    if hasattr(html_out, 'name'):
        # html_out is a file, close after writing
        html_out.close()


def apply_numchapters(get_node_type, binder, numchapters):
    for i, node in enumerate(binder):
        if get_node_type(node) == 'chapter':
            partcount['chapter'] += 1
        elif isinstance(node, cnxepub.TranslucentBinder):
            apply_numchapters(get_node_type, node, numchapters)
        if partcount['chapter'] > numchapters:
            del binder[i]

    logger.debug(' '.join(['{}: {}'.format(name, partcount[name])
                           for name in parts]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assemble complete book "
                                                 "as single HTML file")
    parser.add_argument('epub_file_path',
                        help='Path to the epub file containing the book')
    parser.add_argument("html_out", nargs="?",
                        type=argparse.FileType('w'),
                        help="assembled HTML file output (default stdout)",
                        default=sys.stdout)
    parser.add_argument('-m', "--mathjax_version", const="latest",
                        metavar="mathjax_version", nargs="?",
                        help="Add script tag to use MathJax of given version")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Send debugging info to stderr')
    parser.add_argument('-s', '--subset-chapters', dest='numchapters',
                        type=int, const=2, nargs='?', metavar='num_chapters',
                        help="Create subset of complete book "
                        "(default 2 chapters plus extras)")

    args = parser.parse_args(argv)

    handler = logging.StreamHandler(sys.stderr)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    mathjax_version = args.mathjax_version
    if mathjax_version:
        if not mathjax_version.endswith('latest'):
            mathjax_version += '-latest'

    single_html(args.epub_file_path, args.html_out, mathjax_version,
                args.numchapters)
