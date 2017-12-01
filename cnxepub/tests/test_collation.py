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

    def test_html(self):
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.html')
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
                    'id': 'apple@1.3',
                    'title': 'Apple'
                    },
                    {
                    'shortId': None,
                    'id': 'lemon@1.3',
                    'title': '<span>1.1</span> <span>|</span> <span>&#12524;&#12514;&#12531;</span>'
                    },
                    {
                    'shortId': 'sfE7YYyV@1.3',
                    'id': 'b1f13b61-8c95-5fbe-9112-46400b6dc8de@1.3',
                    'contents': [{
                        'shortId': None,
                        'id': 'lemon@1.3',
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
                        'id': 'chocolate@1.3',
                        'title': u'\u30c1\u30e7\u30b3\u30ec\u30fc\u30c8'
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
            u'print_style': None,
            u'cnx-archive-uri': None,
            u'cnx-archive-shortid': None,
            u'derived_from_title': None,
            u'derived_from_uri': None,
            u'version': None,
            }

        fruity = desserts[0]
        self.assertEqual('Binder', fruity.__class__.__name__)
        self.assertEqual('Fruity', fruity.metadata['title'])

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = base_metadata.copy()
        metadata['title'] = 'Apple'
        metadata['version'] = '1.3'
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
        self.assertEqual(metadata, extra_metadata)


class CollateTestCase(BaseModelTestCase):

    @property
    def target(self):
        from cnxepub.collation import collate
        return collate

    def test(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': 'Book One',
                      'license_url': 'http://my.license',
                      'cnx-archive-uri': 'bad183c3-8776-4a6d-bb02-3b11e0c26aaf'},
            nodes=[
                self.make_document(
                    id="e78d4f90",
                    content=b"<p>document one</p>",
                    metadata={'version': '3',
                              'title': "Document One",
                              'license_url': 'http://my.license'}),
                self.make_document(
                    id="3c448dc6",
                    content=b"<p>document two</p>",
                    metadata={'version': '1',
                              'title': "Document Two",
                              'license_url': 'http://my.license'})])

        # Append a ruleset to the binder.
        ruleset = io.BytesIO(b" ")
        resource = self.make_resource('ruleset', ruleset, 'text/css',
                                      filename='ruleset.css')
        binder.resources.append(resource)

        def mock_easybake(ruleset, in_html, out_html):
            from lxml import etree
            html = etree.parse(in_html)
            # Add in a composite-page with title "Composite One" here.
            body = html.getroot().xpath(
                '//xhtml:body',
                namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]
            comp_elm = etree.SubElement(body, 'div')
            comp_elm.attrib['data-type'] = 'composite-page'
            comp_elm.append(etree.fromstring("""
            <div data-type="metadata">
              <h1 data-type="document-title" itemprop="name">Composite One</h1>
              <div class="authors">
                By:
                Edited by:
                Illustrated by:
                Translated by:
              </div>
              <div class="publishers">
                Published By:
              </div>
              <div class="permissions">
                <p class="license">
                Licensed:
                <a href="" itemprop="dc:license,lrmi:useRightsURL" data-type="license"/>
               </p>
              </div>
              <div class="description" itemprop="description" data-type="description"> </div>
            </div>"""))
            etree.SubElement(comp_elm, 'p').text = "composite document"
            # Add the composite-page to the table-of-contents.
            toc = html.getroot().xpath(
                "//xhtml:*[@id='toc']/xhtml:ol",
                namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})[0]
            etree.SubElement(toc, 'li').append(etree.fromstring('<a>Composite One</a>'))
            out_html.write(etree.tostring(html))

        with mock.patch('cnxepub.collation.easybake') as easybake:
            easybake.side_effect = mock_easybake
            fake_ruleset = 'div::after {contents: "test"}'
            collated_binder = self.target(binder, fake_ruleset)

        # Check for the appended composite document
        self.assertEqual(len(collated_binder), 3)
        self.assertEqual(collated_binder[2].id, 'a9428a6c-5d31-5425-8335-8a2e780651e0')
        self.assertEqual(collated_binder[2].metadata['title'],
                         'Composite One')

    def test_without_ruleset(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One",
                      'license_url': 'http://my.license'},
            nodes=[
                self.make_document(
                    id="e78d4f90",
                    metadata={'version': '3',
                              'title': "Document One",
                              'license_url': 'http://my.license'}),
                self.make_document(
                    id="3c448dc6",
                    metadata={'version': '1',
                              'title': "Document Two",
                              'license_url': 'http://my.license'})])

        result = self.target(binder)
        self.assertIs(binder, result)

    def test_with_ruleset(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One",
                      'license_url': 'http://my.license'},
            nodes=[
                self.make_document(
                    id="e78d4f90",
                    content=b"<span>document one</span>",
                    metadata={'version': '3',
                              'title': "Document One",
                              'license_url': 'http://my.license'}),
                self.make_document(
                    id="3c448dc6",
                    content=b"<span>document two</span>",
                    metadata={'version': '1',
                              'title': "Document Two",
                              'license_url': 'http://my.license'})])

        # Append a ruleset to the binder.
        ruleset_bytes = b"""\
div[data-type='page'] > div[data-type='metadata'] {
  copy-to: eob-all
}
div[data-type='page'] span {
  copy-to: eob-all
}
body::after {
  content: pending(eob-all);
  class: end-of-book;
  data-type: composite-page;
  container: div;
}

/* copied from cte books/rulesets/common/toc.less */
body > div[data-type="page"],
body > div[data-type="composite-page"]:pass(20) {
  string-set: page-id attr(id);
}
body > div[data-type="page"] > div[data-type="metadata"] > \
    h1[data-type='document-title'],
body > div[data-type="composite-page"] > div[data-type="metadata"] > \
        h1[data-type='document-title']:pass(20) {
  copy-to: page-title;
}
body > div[data-type="page"]::after,
body > div[data-type="composite-page"]:pass(20)::after {
  content: pending(page-title);
  attr-href: "#" string(page-id);
  container: a;
  move-to: page-link;
}
body > div[data-type="page"]::after,
body > div[data-type="composite-page"]:pass(20)::after {
  content: pending(page-link);
  move-to: eob-toc;
  container: li;
}
nav#toc:pass(30) {
  content: '';
}
nav#toc:pass(30)::after {
  content: pending(eob-toc);
  container: ol;
}
"""
        resource = self.make_resource('ruleset',
                                      io.BytesIO(ruleset_bytes),
                                      'text/css',
                                      filename='ruleset.css')
        binder.resources.append(resource)

        collated_binder = self.target(binder, ruleset_bytes)

        # Check for the appended composite document
        self.assertEqual(len(collated_binder), 3)
        self.assertEqual(collated_binder[2].metadata['title'],
                         'Document One')
