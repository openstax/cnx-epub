# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Processes a collated book's single-html representation for validation.

Ensures safe parsing for specific elements.
"""
from __future__ import print_function
import argparse
import logging
import sys
from pprint import pformat
import cnxepub
from zipfile import ZipFile, ZIP_DEFLATED

logger = logging.getLogger('cnxepub')

formatter = logging.Formatter('%(name)s %(levelname)s %(message)s')
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
logger.addHandler(handler)


def main(argv=None):
    """Parse passed in cooked single HTML."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collated_html', type=argparse.FileType('r'),
                        help='Path to the collated html'
                             ' file (use - for stdin)')
    parser.add_argument('-d', '--dump-tree', action='store_true',
                        help='Print out parsed model tree.')

    parser.add_argument('-o', '--output', type=argparse.FileType('w+'),
                        help='Write out epub of parsed tree.')

    parser.add_argument('-i', '--input', type=argparse.FileType('r'),
                        help='Read and copy resources/ for output epub.')

    args = parser.parse_args(argv)

    if args.input and args.output == sys.stdout:
        raise ValueError('Cannot output to stdout if reading resources')

    from cnxepub.collation import reconstitute
    binder = reconstitute(args.collated_html)

    if args.dump_tree:
        print(pformat(cnxepub.model_to_tree(binder)),
              file=sys.stdout)
    if args.output:
        cnxepub.adapters.make_epub(binder, args.output)

    if args.input:
        args.output.seek(0)
        zout = ZipFile(args.output, 'a', ZIP_DEFLATED)
        zin = ZipFile(args.input, 'r')
        for res in zin.namelist():
            if res.startswith('resources'):
                zres = zin.open(res)
                zi = zin.getinfo(res)
                zout.writestr(zi, zres.read(), ZIP_DEFLATED)
        zout.close()

    # TODO Check for documents that have no identifier.
    #      These should likely be composite-documents
    #      or the the metadata got wiped out.
    # docs = [x for x in cnxepub.flatten_to(binder, only_documents_filter)
    #         if x.ident_hash is None]

    return 0
