# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import mimetypes
import os
import io
import tempfile
import shutil
import random
import re
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from ..testing import TEST_DATA_DIR, unescape


def random_extension(*args, **kwargs):
    # mimetypes.guess_extension can return any of the values in
    # mimetypes.guess_all_extensions.  it depends on the system.
    # we're using this to make sure our code is robust enough to handle the
    # different possible extensions
    exts = mimetypes.guess_all_extensions(*args, **kwargs)
    return random.choice(exts)


class HTMLAdaptationTestCase(unittest.TestCase):
    page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.xhtml')
    maxDiff = None
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
        u'language': 'en',
        u'cnx-archive-uri': None,
        u'cnx-archive-shortid': None,
        u'derived_from_title': None,
        u'derived_from_uri': None,
        u'version': None,
        u'canonical_book_uuid': None,
        u'slug': None,
        }

    def test_from_formatter_to_adapter(self):
        from ..adapters import adapt_single_html
        from ..formatters import SingleHTMLFormatter
        from ..models import Binder, Document, DocumentPointer

        metadata = self.base_metadata.copy()
        binder = Binder(metadata['title'], metadata=metadata)
        binder.append(Document('apple-pie', io.BytesIO(b'<body><p>Apple Pie</p></body>'),
                               metadata=metadata))
        binder.append(Document('lemon-pie', io.BytesIO(b'''\
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Lemon Pie</title>
    </head>
    <body>
        <h1>Lemon Pie</h1>
        <p>Yum.</p>
        <p id="dupe">Yum.</p>
        <p id="dupe">Yum.</p>
    </body>
</html>'''), metadata=metadata))
        binder.append(DocumentPointer('content-ident-hash', metadata={
            'title': 'Test Document Pointer',
            'url': 'https://cnx.org/'}))

        single_html = str(SingleHTMLFormatter(binder))
        adapted_binder = adapt_single_html(single_html)

        self.assertEqual(len(adapted_binder), len(binder))
        self.assertEqual(adapted_binder[0].id, 'page_apple-pie')
        self.assertEqual(adapted_binder[1].id, 'page_lemon-pie')
        self.assertEqual(adapted_binder[0].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="page_apple-pie"><p>Apple Pie</p>
  </div></body>''')
        self.assertEqual(adapted_binder[1].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="page_lemon-pie">\
<h1>Lemon Pie</h1>\n        \n        <p>Yum.</p>\n        \n        <p id="dupe">Yum.</p>\n        \n        <p id="dupe0">Yum.</p>\n    \n    \n  \
</div></body>'''.format(0, 0))
        self.assertEqual(adapted_binder[2].id, 'page_content-ident-hash')
        self.assertEqual(adapted_binder[2].metadata['title'],
                         'Test Document Pointer')
        self.assertEqual(adapted_binder[2].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="page_content-\
ident-hash"><div>
      <p>
        Click <a href="https://cnx.org/">here</a> to read Test Document \
Pointer.
      </p>
    </div>
  </div></body>''')

    def test_to_binder(self):
        from ..adapters import adapt_single_html
        from ..models import model_to_tree

        with open(self.page_path, 'r') as f:
            html = f.read()

        desserts = adapt_single_html(html)
        self.assertEqual('Desserts', desserts.metadata['title'])

        self.assertEqual({
            'shortId': None,
            'id': '00000000-0000-0000-0000-000000000000@1.3',
            'contents': [
                {
                    'shortId': 'frt',
                    'id': 'ec84e75d-9973-41f1-ab9d-1a3ebaef87e2@1.3',
                    'contents': [
                        {
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
                            'contents': [
                                {
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
            'title': 'Desserts'
            }, model_to_tree(desserts))

        fruity = desserts[0]
        self.assertEqual('Binder', fruity.__class__.__name__)
        self.assertEqual('Fruity', fruity.metadata['title'])
        self.assertEqual('ec84e75d-9973-41f1-ab9d-1a3ebaef87e2@1.3', fruity.metadata['id'])
        self.assertEqual('frt', fruity.metadata['shortId'])
        self.assertEqual('Fruity', desserts.get_title_for_node(fruity))

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = self.base_metadata.copy()
        metadata['title'] = 'Apple'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        metadata['canonical_book_uuid'] = 'ea4244ce-dd9c-4166-9c97-acae5faf0ba1'
        apple_metadata = apple.metadata.copy()
        summary = etree.fromstring(apple_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, apple_metadata)
        self.assertIn(b'<p>'
                      b'<a href="/contents/page_lemon">Link to lemon</a>. '
                      b'Here are some examples:</p>',
                      apple.content)
        self.assertEqual('Apple', fruity.get_title_for_node(apple))

        lemon = fruity[1]
        self.assertEqual('Document', lemon.__class__.__name__)
        metadata = self.base_metadata.copy()
        metadata['title'] = 'Lemon'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        lemon_metadata = lemon.metadata.copy()
        summary = etree.fromstring(lemon_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, lemon_metadata)
        self.assertIn(b'<p>Yum! <img src="/resources/1x1.jpg"'
                      b'/></p>', lemon.content)
        self.assertEqual(u'<span>1.1</span> <span>|</span> <span>'
                         u'レモン</span>',
                         fruity.get_title_for_node(lemon))

        citrus = fruity[2]
        self.assertEqual('Binder', citrus.__class__.__name__)
        self.assertEqual(citrus.metadata['title'], 'Citrus')

        self.assertEqual(lemon.metadata, citrus[0].metadata)
        self.assertEqual('<span>Chapter</span> <span>2</span> '
                         '<span>citrus</span>',
                         fruity.get_title_for_node(citrus))

        chocolate = desserts[1]
        self.assertEqual('Document', chocolate.__class__.__name__)
        chocolate_metadata = chocolate.metadata.copy()
        summary = etree.fromstring(chocolate_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = self.base_metadata.copy()
        metadata['title'] = u'チョコレート'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        self.assertEqual(metadata, chocolate_metadata)
        self.assertIn(b'<p><a href="#list">List</a> of',
                      chocolate.content)
        self.assertIn(b'<div data-type="list" id="list"><ul>',
                      chocolate.content)
        self.assertEqual(u'チョコレート',
                         desserts.get_title_for_node(chocolate))

        extra = desserts[2]
        self.assertEqual('CompositeDocument', extra.__class__.__name__)
        extra_metadata = extra.metadata.copy()
        summary = etree.fromstring(extra_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        metadata = self.base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        metadata['version'] = '1.3'
        metadata['revised'] = '2013/03/05 09:35:24 -0500'
        self.assertEqual(metadata, extra_metadata)
        self.assertIn(b'<p>Here is a <a href="/contents/page_chocolate'
                      b'#list">link</a> to another document.</p>',
                      extra.content)
        self.assertEqual('Extra Stuff', desserts.get_title_for_node(extra))

    def test_missing_title_override(self):
        """Throw error if override titles are missing."""
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page-bad.xhtml')
        from ..adapters import adapt_single_html
        from ..models import model_to_tree

        with open(page_path, 'r') as f:
            html = f.read()

        with self.assertRaises(AssertionError) as caught_exception:
            desserts = adapt_single_html(html)

    def test_title_utf8_umlaut_uuid5_generation(self):
        """Test UTF8 in metadata title with uuid5 generation."""
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page-umlaut.xhtml')
        from ..adapters import adapt_single_html
        from ..models import model_to_tree

        with open(page_path, 'r') as f:
            html = f.read()

        try:
            desserts = adapt_single_html(html)
        except Exception as e:
            self.fail('utf8 uuid5 test failed: ' + str(e))

    def test_unknown_data_type(self):
        """Throw error if unknown data-type in HTML"""
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page-bad-type.xhtml')
        from ..adapters import adapt_single_html
        from ..models import model_to_tree

        with open(page_path, 'r') as f:
            html = f.read()

        with self.assertRaises(AssertionError) as caught_exception:
            desserts = adapt_single_html(html)

    def test_fix_generated_ids_in_composite_page(self):
        from ..adapters import adapt_single_html

        page_path = os.path.join(TEST_DATA_DIR,
                                 'collated-desserts-single-page.xhtml')
        with open(page_path, 'r') as f:
            html = f.read()

        desserts = adapt_single_html(html)

        lemon = desserts[0][1][0]
        chocolate = desserts[1]
        extra = desserts[2]

        self.assertIn(b'<p id="1">Content moved from another page.</p>',
                      extra.content)
        self.assertIn(b'Click <a href="/contents/9f7dce40-0de7-5a29-a416-a9cf8eedf4d4#1">here</a>',
                      chocolate.content)
        self.assertIn(b'<p id="summary0"> Pretend move of lemon summary</p>',
                      extra.content)
        self.assertIn(b'<p id="summary1"> Pretend move of chocolate summary</p>',
                      extra.content)
        self.assertIn(b'<p id="myid">Be sure to read the <a href="/contents/9f7dce40-0de7-5a29-a416-a9cf8eedf4d4#summary0">Summary for lemon</a></p>', lemon.content)

    def test_fix_generated_ids_links_without_version(self):
        from ..adapters import adapt_single_html

        page_path = os.path.join(TEST_DATA_DIR,
                                 'collated-desserts-single-page.xhtml')

        with open(page_path, 'r') as f:
            html = f.read()

        desserts = adapt_single_html(html)
        apple = desserts[0][0]
        self.assertIn(b'<p><a href="/contents/chocolate">',
                      apple.content)

    @mock.patch('cnxepub.adapters.logger')
    def test_missing_required_metadata(self, logger):
        from ..adapters import adapt_single_html

        page_path = os.path.join(TEST_DATA_DIR,
                                 'collated-desserts-single-page.xhtml')

        with open(page_path, 'r') as f:
            html = f.read()

        html = html.replace(
            '<h1 data-type="document-title" itemprop="name">Apple</h1>',
            '<h1 data-type="document-title" itemprop="name"></h1>')

        self.assertRaises(ValueError, adapt_single_html, html)

    @mock.patch('cnxepub.adapters.logger')
    def test_missing_metadata_element(self, logger):
        from ..adapters import adapt_single_html

        page_path = os.path.join(TEST_DATA_DIR,
                                 'collated-desserts-single-page.xhtml')

        with open(page_path, 'r') as f:
            html = f.read()

        html = html.replace(
            '<div data-type="page" id="apple">\n<div data-type="metadata">',
            '<div data-type="page" id="apple">\n<div>')

        self.assertRaises(IndexError, adapt_single_html, html)
