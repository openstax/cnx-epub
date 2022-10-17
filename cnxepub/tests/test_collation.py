# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import io
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from .test_models import BaseModelTestCase


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


class ReconstituteTestCase(unittest.TestCase):
    maxDiff = None

    def test_xhtml(self):
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.xhtml')
        with open(page_path) as html:
            from cnxepub.collation import reconstitute
            desserts = reconstitute(html)
        self.check_desserts(desserts)

    def check_desserts(self, desserts):
        """Assertions for the desserts model"""
        from ..models import model_to_tree

        self.assertEqual('Desserts', desserts.metadata['title'])

        self.assertEqual({
            'shortId': None,
            'id': '00000000-0000-0000-0000-000000000000@1.3',
            'contents': [{
                'shortId': 'frt',
                'id': 'ec84e75d-9973-41f1-ab9d-1a3ebaef87e2@1.3',
                'contents': [{
                    'shortId': None,
                    'id': 'page_apple@1.3',
                    'title': 'Apple'
                    },
                    {
                    'shortId': None,
                    'id': 'page_lemon@1.3',
                    'title': u'<span>1.1</span> <span>|</span> <span>レモン</span>'
                    },
                    {
                    'shortId': 'sfE7YYyV@1.3',
                    'id': 'b1f13b61-8c95-5fbe-9112-46400b6dc8de@1.3',
                    'contents': [{
                        'shortId': None,
                        'id': 'page_lemon@1.3',
                        'title': 'Lemon'
                        }
                        ],
                    'title': '<span>Chapter</span> <span>2</span> <span>citrus</span>'
                    }
                    ],
                'title': 'Fruity'
                    },
                    {
                        'shortId': None,
                        'id': 'page_chocolate@1.3',
                        'title': u'チョコレート'
                    },
                    {
                        'shortId': None,
                        'id': 'extra@1.3',
                        'title': 'Extra Stuff'
                    }
                    ],
                'title': 'Desserts'}, model_to_tree(desserts))

        base_metadata = {
            u'publishers': [],
            u'created': None,  # '2016/03/04 17:05:20 -0500',
            u'revised': None,  # '2013/03/05 09:35:24 -0500',
            u'authors': [
                {u'type': u'cnx-id',
                 u'name': u'Good Food',
                 u'id': u'yum'}],
            u'editors': [],
            u'copyright_holders': [],
            u'illustrators': [],
            u'subjects': [u'Humanities'],
            u'translators': [],
            u'keywords': [u'Food', u'デザート', u'Pudding'],
            u'title': u'チョコレート',
            u'license_text': u'CC-By 4.0',
            u'license_url': u'http://creativecommons.org/licenses/by/4.0/',
            # 'version': 'draft',
            u'language': 'en',
            u'cnx-archive-uri': None,
            u'cnx-archive-shortid': None,
            u'derived_from_title': None,
            u'derived_from_uri': None,
            u'version': None,
            u'canonical_book_uuid': None,
            u'slug': None,
            }

        fruity = desserts[0]
        self.assertEqual('Binder', fruity.__class__.__name__)
        self.assertEqual('Fruity', fruity.metadata['title'])

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Apple'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        metadata['canonical_book_uuid'] = 'ea4244ce-dd9c-4166-9c97-acae5faf0ba1'
        apple_metadata = apple.metadata.copy()
        summary = etree.fromstring(apple_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, apple_metadata)

        lemon = fruity[1]
        self.assertEqual('Document', lemon.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Lemon'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        apple_metadata = apple.metadata.copy()
        lemon_metadata = lemon.metadata.copy()
        summary = etree.fromstring(lemon_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, lemon_metadata)

        citrus = fruity[2]
        self.assertEqual('Binder', citrus.__class__.__name__)
        self.assertEqual(citrus.metadata['title'], 'Citrus')

        self.assertEqual(lemon.metadata, citrus[0].metadata)

        chocolate = desserts[1]
        self.assertEqual('Document', chocolate.__class__.__name__)
        chocolate_metadata = chocolate.metadata.copy()
        summary = etree.fromstring(chocolate_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = base_metadata.copy()
        metadata['title'] = u'チョコレート'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        apple_metadata = apple.metadata.copy()
        self.assertEqual(metadata, chocolate_metadata)

        extra = desserts[2]
        self.assertEqual('CompositeDocument', extra.__class__.__name__)
        extra_metadata = extra.metadata.copy()
        summary = etree.fromstring(extra_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        self.assertEqual(metadata, extra_metadata)

    def test_xhtml_with_ampersand_title_person_license(self):
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page-ampersand.xhtml')
        with open(page_path) as html:
            from cnxepub.collation import reconstitute
            desserts = reconstitute(html)
        self.check_desserts_ampersand(desserts)

    def check_desserts_ampersand(self, desserts):
        """Assertions for the desserts model"""
        from ..models import model_to_tree

        self.assertEqual('Desserts & even more desserts', desserts.metadata['title'])

        self.assertEqual({
            'shortId': None,
            'id': '00000000-0000-0000-0000-000000000000@1.3',
            'contents': [{
                'shortId': 'frt',
                'id': 'ec84e75d-9973-41f1-ab9d-1a3ebaef87e2@1.3',
                'contents': [{
                    'shortId': None,
                    'id': 'page_apple@1.3',
                    'title': 'Apple'
                    },
                    {
                    'shortId': None,
                    'id': 'page_lemon@1.3',
                    'title': u'<span>1.1</span> <span>|</span> <span>レモン</span>'
                    },
                    {
                    'shortId': 'sfE7YYyV@1.3',
                    'id': 'b1f13b61-8c95-5fbe-9112-46400b6dc8de@1.3',
                    'contents': [{
                        'shortId': None,
                        'id': 'page_lemon@1.3',
                        'title': 'Lemon'
                        }
                        ],
                    'title': '<span>Chapter</span> <span>2</span> <span>citrus</span>'
                    }
                    ],
                'title': 'Fruity'
                    },
                    {
                        'shortId': None,
                        'id': 'page_chocolate@1.3',
                        'title': u'チョコレート'
                    },
                    {
                        'shortId': None,
                        'id': 'extra@1.3',
                        'title': 'Extra Stuff'
                    }
                    ],
                'title': 'Desserts & even more desserts'}, model_to_tree(desserts))

        base_metadata = {
            u'publishers': [],
            u'created': None,  # '2016/03/04 17:05:20 -0500',
            u'revised': None,  # '2013/03/05 09:35:24 -0500',
            u'authors': [
                {u'type': u'cnx-id',
                 u'name': u'Mario&Luigi',
                 u'id': u'yum'}],
            u'editors': [],
            u'copyright_holders': [],
            u'illustrators': [],
            u'subjects': [u'Humanities'],
            u'translators': [],
            u'keywords': [u'Food', u'デザート', u'Pudding'],
            u'title': u'チョコレート',
            u'license_text': u'CC-By 4.0 & MyDessert',
            u'license_url': u'http://creativecommons.org/licenses/by/4.0/',
            # 'version': 'draft',
            u'language': 'en',
            u'cnx-archive-uri': None,
            u'cnx-archive-shortid': None,
            u'derived_from_title': None,
            u'derived_from_uri': None,
            u'version': None,
            u'canonical_book_uuid': None,
            u'slug': None,
            }

        fruity = desserts[0]
        self.assertEqual('Binder', fruity.__class__.__name__)
        self.assertEqual('Fruity', fruity.metadata['title'])

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Apple'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        metadata['canonical_book_uuid'] = 'ea4244ce-dd9c-4166-9c97-acae5faf0ba1'
        apple_metadata = apple.metadata.copy()
        summary = etree.fromstring(apple_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, apple_metadata)

        lemon = fruity[1]
        self.assertEqual('Document', lemon.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Lemon'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        apple_metadata = apple.metadata.copy()
        lemon_metadata = lemon.metadata.copy()
        summary = etree.fromstring(lemon_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, lemon_metadata)

        citrus = fruity[2]
        self.assertEqual('Binder', citrus.__class__.__name__)
        self.assertEqual(citrus.metadata['title'], 'Citrus')

        self.assertEqual(lemon.metadata, citrus[0].metadata)

        chocolate = desserts[1]
        self.assertEqual('Document', chocolate.__class__.__name__)
        chocolate_metadata = chocolate.metadata.copy()
        summary = etree.fromstring(chocolate_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = base_metadata.copy()
        metadata['title'] = u'チョコレート'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        apple_metadata = apple.metadata.copy()
        self.assertEqual(metadata, chocolate_metadata)

        extra = desserts[2]
        self.assertEqual('CompositeDocument', extra.__class__.__name__)
        extra_metadata = extra.metadata.copy()
        summary = etree.fromstring(extra_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        self.assertEqual(metadata, extra_metadata)
