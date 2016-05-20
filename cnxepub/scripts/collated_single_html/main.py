# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""\
Processes a collated book's single-html representation for validation
and parser of specific elements.

"""
import argparse
import os
import sys
from pprint import pprint

import cnxepub


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('collated_html', type=argparse.FileType('r'),
                        help='Path to the collated html file (use - for stdin)')
    args = parser.parse_args(argv)

    binder = cnxepub.adapt_single_html(args.collated_html.read())
    pprint(cnxepub.model_to_tree(binder))

    # TODO Check for documents that have no identifier.
    #      These should likely be composite-documents
    #      or the the metadata got whiped out.
    # docs = [x for x in cnxepub.flatten_to(binder, only_documents_filter)
    #         if x.ident_hash is None]

    return 0
