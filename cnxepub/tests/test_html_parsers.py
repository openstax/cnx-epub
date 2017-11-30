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
        expected_metadata = {
            'summary': None,
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
            'cnx-archive-uri': 'e78d4f90-e078-49d2-beac-e95e8be70667@3',
            'cnx-archive-shortid': '541PkOB4@3',
            'derived_from_uri': 'http://example.org/contents/id@ver',
            'derived_from_title': 'Wild Grains and Warted Feet',
            'print_style': '* print style *',
            'language': 'en',
            'version': '3',
            }
        self.assertEqual(metadata, expected_metadata)
