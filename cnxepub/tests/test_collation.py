# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

from .test_models import BaseModelTestCase


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


@unittest.skip("not implemented")
class XXXEasyBakeTestCase(unittest.TestCase):

    def test(self):
        import io
        _input = """
<html><body>
<div data-type="book">
  <div data-type="page">
    <span>content</span>
  </div>
</div>
</body></html>"""
        input = io.BytesIO(_input)
        output = io.BytesIO()

        # Ensure same in, same out
        from cnxepub.collation import easybake
        easybake('ruleset', input, output)
        output.seek(0)

        self.assertIn(output.read(), "<span> pseudo cooked </span>")


class ReconstituteTestCase(unittest.TestCase):

    def test(self):
        from lxml import etree
        from ..models import model_to_tree

        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.html')
        with open(page_path) as f:
            html = f.read()

        from cnxepub.collation import reconstitute
        desserts = reconstitute(html)

        self.assertEqual('Desserts', desserts.metadata['title'])

        self.assertEqual({
            'id': 'book',
            'title': 'Desserts',
            'contents': [
                {
                    'id': 'subcol',
                    'title': 'Fruity',
                    'contents': [
                        {
                            'id': 'Apple',
                            'title': 'Apple',
                            },
                        {
                            'id': 'Lemon',
                            'title': 'Lemon',
                            },
                        {
                            'id': 'subcol',
                            'title': 'Citrus',
                            'contents': [
                                {
                                    'id': 'Lemon',
                                    'title': 'Lemon',
                                    },
                                ],
                            },
                        ],
                    },
                {
                    'id': u'チョコレート',
                    'title': u'チョコレート',
                    },
                {
                    'id': 'Extra Stuff',
                    'title': 'Extra Stuff',
                    },
                ],
            }, model_to_tree(desserts))

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
            u'language': None,
            u'print_style': None,
            u'cnx-archive-uri': None,
            u'derived_from_title': None,
            u'derived_from_uri': None,
            }

        fruity = desserts[0]
        self.assertEqual('TranslucentBinder', fruity.__class__.__name__)
        self.assertEqual('Fruity', fruity.metadata['title'])

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Apple'
        apple_metadata = apple.metadata.copy()
        summary = etree.fromstring(apple_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, apple_metadata)

        lemon = fruity[1]
        self.assertEqual('Document', lemon.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Lemon'
        lemon_metadata = lemon.metadata.copy()
        summary = etree.fromstring(lemon_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, lemon_metadata)

        citrus = fruity[2]
        self.assertEqual('TranslucentBinder', citrus.__class__.__name__)
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
        self.assertEqual(metadata, chocolate_metadata)

        extra = desserts[2]
        self.assertEqual('CompositeDocument', extra.__class__.__name__)
        extra_metadata = extra.metadata.copy()
        summary = etree.fromstring(extra_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        self.assertEqual(metadata, extra_metadata)


class CollateTestCase(BaseModelTestCase):

    @property
    def target(self):
        from cnxepub import collate
        return collate

    @unittest.skip("work in progress")
    def test(self):
        self.fail("work in progress")

    def test_without_ruleset(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_document(
                    id="e78d4f90",
                    metadata={'version': '3',
                              'title': "Document One"}),
                self.make_document(
                    id="3c448dc6",
                    metadata={'version': '1',
                              'title': "Document Two"})])

        result = self.target(binder)
        self.assertIs(binder, result)
