# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

from lxml import etree


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


class HTMLParsingTestCase(unittest.TestCase):
    maxDiff = None

    def test_metadata_parsing(self):
        """Verify the parsing of metadata from an HTML document."""
        html_doc_filepath = os.path.join(
            TEST_DATA_DIR, 'book', 'content',
            'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml')
        from ..html_parsers import parse_metadata
        with open(html_doc_filepath, 'r') as fb:
            html = etree.parse(fb)
            metadata = parse_metadata(html)
        summary = b"""<div xmlns="http://www.w3.org/1999/xhtml" xmlns:bib="http://bibtexml.sf.net/" xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:epub="http://www.idpf.org/2007/ops" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:lrmi="http://lrmi.net/the-specification" class="description" itemprop="description" data-type="description">\n        By the end of this section, you will be able to: \n        <ul class="list">\n          <li class="item">Drive a car</li>\n          <li class="item">Purchase a watch</li>\n          <li class="item">Wear funny hats</li>\n          <li class="item">Eat cake</li>\n        </ul>\n      </div>\n\n      """
        expected_metadata = {
            'summary': summary,
            'authors': [
                {'id': 'https://github.com/marknewlyn',
                 'name': 'Mark Horner',
                 'type': 'github-id'},
                {'id': 'https://cnx.org/member_profile/sarblyth',
                 'name': 'Sarah Blyth',
                 'type': 'cnx-id'},
                {'id': 'https://example.org/profiles/charrose',
                 'name': 'Charmaine St. Rose',
                 'type': 'openstax-id'}],
            'copyright_holders': [
                {'id': 'https://cnx.org/member_profile/ream',
                 'name': 'Ream',
                 'type': 'cnx-id'}],
            'created': '2013/03/19 15:01:16 -0500',
            'editors': [{'id': None, 'name': 'I. M. Picky', 'type': None}],
            'illustrators': [{'id': None, 'name': 'Francis Hablar',
                              'type': None}],
            'keywords': ['South Africa'],
            'license_text': 'CC-By 4.0',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'publishers': [{'id': None, 'name': 'Ream', 'type': None}],
            'revised': '2013/06/18 15:22:55 -0500',
            'subjects': ['Science and Mathematics'],
            'title': 'Document One of Infinity',
            'translators': [{'id': None, 'name': 'Francis Hablar',
                             'type': None}],
            'cnx-archive-uri': 'e78d4f90-e078-49d2-beac-e95e8be70667',
            'derived_from_uri': 'http://example.org/contents/id@ver',
            'derived_from_title': 'Wild Grains and Warted Feet',
            }
        self.assertEqual(metadata, expected_metadata)
