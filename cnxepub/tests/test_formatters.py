# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import io
import mimetypes
import os
import sys
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from ..testing import TEST_DATA_DIR, unescape


IS_PY3 = sys.version_info.major == 3


def last_extension(*args, **kwargs):
    # Always return the last value of sorted mimetypes.guess_all_extensions
    exts = mimetypes.guess_all_extensions(*args, **kwargs)
    return sorted(exts)[-1]


class DocumentContentFormatterTestCase(unittest.TestCase):
    def test_document(self):
        from ..models import Document
        from ..formatters import DocumentContentFormatter

        base_metadata = {
            'publishers': [],
            'created': '2013/03/19 15:01:16 -0500',
            'revised': '2013/06/18 15:22:55 -0500',
            'authors': [
                {'type': 'cnx-id',
                 'name': 'Sponge Bob',
                 'id': 'sbob'}],
            'editors': [],
            'copyright_holders': [],
            'illustrators': [],
            'subjects': ['Science and Mathematics'],
            'translators': [],
            'keywords': ['Bob', 'Sponge', 'Rock'],
            'title': "Goofy Goober Rock",
            'license_text': 'CC-By 4.0',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'summary': "<p>summary</p>",
            'version': 'draft',
            }

        # Build test document.
        metadata = base_metadata.copy()
        document = Document('title',
                            io.BytesIO(u'<p>コンテンツ...</p>'.encode('utf-8')),
                            metadata=metadata)
        html = str(DocumentContentFormatter(document))
        expected_html = u"""\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body><p>コンテンツ...</p></body>
</html>"""
        self.assertEqual(expected_html, unescape(html))


class DocumentSummaryFormatterTestCase(unittest.TestCase):
    def test_summary_w_one_tag(self):
        from ..formatters import DocumentSummaryFormatter
        from ..models import Document

        document = Document('title', io.BytesIO(b'contents'),
                            metadata={'summary': '<p>résumé</p>'})
        html = str(DocumentSummaryFormatter(document))
        self.assertEqual('<p>résumé</p>', html)

    def test_summary_w_just_text(self):
        from ..formatters import DocumentSummaryFormatter
        from ..models import Document

        document = Document('title', io.BytesIO(b'contents'),
                            metadata={'summary': 'résumé'})
        html = str(DocumentSummaryFormatter(document))
        expected = """\
<div class="description" data-type="description"\
 xmlns="http://www.w3.org/1999/xhtml">
  résumé
</div>"""
        self.assertEqual(expected, html)

    def test_summary_w_text_and_tags(self):
        from ..formatters import DocumentSummaryFormatter
        from ..models import Document

        document = Document('title', io.BytesIO(b'contents'),
                            metadata={'summary': 'résumé<p>etc</p><p>...</p>'})
        html = str(DocumentSummaryFormatter(document))
        expected = """\
<div class="description" data-type="description"\
 xmlns="http://www.w3.org/1999/xhtml">
  résumé<p>etc</p><p>...</p>
</div>"""
        self.assertEqual(expected, html)


@mock.patch('mimetypes.guess_extension', last_extension)
class HTMLFormatterTestCase(unittest.TestCase):
    base_metadata = {
        'publishers': [],
        'created': '2013/03/19 15:01:16 -0500',
        'revised': '2013/06/18 15:22:55 -0500',
        'authors': [
            {'type': 'cnx-id',
             'name': 'Sponge Bob',
             'id': 'sbob'}],
        'editors': [],
        'copyright_holders': [],
        'illustrators': [],
        'subjects': ['Science and Mathematics'],
        'translators': [],
        'keywords': ['Bob', 'Sponge', 'Rock'],
        'title': 'タイトル',
        'license_text': 'CC-By 4.0',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'summary': "<p>summary</p>",
        'version': 'draft',
        }

    def xpath(self, path):
        from ..html_parsers import HTML_DOCUMENT_NAMESPACES

        return self.root.xpath(path, namespaces=HTML_DOCUMENT_NAMESPACES)

    def test_document(self):
        from ..models import Document
        from ..formatters import HTMLFormatter

        # Build test document.
        metadata = self.base_metadata.copy()
        document = Document(
            metadata['title'],
            io.BytesIO(u'<p>コンテンツ...</p>'.encode('utf-8')),
            metadata=metadata)

        html = str(HTMLFormatter(document))
        html = unescape(html)
        self.root = etree.fromstring(html.encode('utf-8'))

        self.assertIn(u'<title>タイトル</title>', html)
        self.assertIn(u'<p>コンテンツ...</p>', html)

        self.assertEqual(
            u'タイトル',
            self.xpath('//*[@data-type="document-title"]/text()')[0])

        self.assertEqual(
            'summary',
            self.xpath('//*[@class="description"]/xhtml:p/text()')[0])

        self.assertEqual(
            metadata['created'],
            self.xpath('//xhtml:meta[@itemprop="dateCreated"]/@content')[0])

        self.assertEqual(
            metadata['revised'],
            self.xpath('//xhtml:meta[@itemprop="dateModified"]/@content')[0])

    def test_document_pointer(self):
        from ..models import DocumentPointer
        from ..formatters import HTMLFormatter

        # Build test document pointer.
        pointer = DocumentPointer('pointer@1', {
            'title': self.base_metadata['title'],
            'cnx-archive-uri': 'pointer@1',
            'url': 'https://cnx.org/contents/pointer@1',
            })

        html = str(HTMLFormatter(pointer))
        html = unescape(html)
        self.root = etree.fromstring(html.encode('utf-8'))

        self.assertIn(u'<title>タイトル</title>', html)
        self.assertIn(
            u'<a href="https://cnx.org/contents/pointer@1">', html)

        self.assertEqual(
            u'タイトル',
            self.xpath('//*[@data-type="document-title"]/text()')[0])

        self.assertEqual(
            'pointer@1',
            self.xpath('//*[@data-type="cnx-archive-uri"]/@data-value')[0])

    def test_binder(self):
        from ..models import (Binder, TranslucentBinder, Document,
                              DocumentPointer)
        from ..formatters import HTMLFormatter

        # Build test binder.
        binder = Binder(self.base_metadata['title'], metadata={
            'title': self.base_metadata['title'],
            })

        metadata = self.base_metadata.copy()
        metadata.update({
            'title': "entrée",
            'derived_from_uri': 'http://cnx.org/contents/'
                                'dd68a67a-11f4-4140-a49f-b78e856e2262@1',
            'derived_from_title': "Taking Customers' Orders",
            })

        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))

        translucent_binder = TranslucentBinder(metadata={'title': 'Kranken'})
        binder.append(translucent_binder)

        metadata = self.base_metadata.copy()
        metadata.update({
            'title': "egress",
            'cnx-archive-uri': 'e78d4f90-e078-49d2-beac-e95e8be70667'})
        translucent_binder.append(
            Document('egress', io.BytesIO(u'<p>hüvasti.</p>'.encode('utf-8')),
                     metadata=metadata))

        binder.append(DocumentPointer('pointer@1', {
            'title': 'Pointer',
            'cnx-archive-uri': 'pointer@1',
            'url': 'http://cnx.org/contents/pointer@1'}))

        html = str(HTMLFormatter(binder))
        html = unescape(html)
        self.root = etree.fromstring(html.encode('utf-8'))

        self.assertIn(u'<title>タイトル</title>', html)

        lis = self.xpath('//xhtml:nav/xhtml:ol/xhtml:li')
        self.assertEqual(3, len(lis))
        self.assertEqual('ingress@draft.xhtml', lis[0][0].attrib['href'])
        self.assertEqual(u'entrée', lis[0][0].text)
        self.assertEqual('Kranken', lis[1][0].text)
        self.assertEqual('pointer@1.xhtml', lis[2][0].attrib['href'])
        self.assertEqual('Pointer', lis[2][0].text)

        lis = self.xpath('//xhtml:nav/xhtml:ol/xhtml:li[2]/xhtml:ol/xhtml:li')
        self.assertEqual(1, len(lis))
        self.assertEqual('egress@draft.xhtml', lis[0][0].attrib['href'])
        self.assertEqual('egress', lis[0][0].text)

    def test_translucent_binder(self):
        from ..models import (TranslucentBinder, Document)
        from ..formatters import HTMLFormatter

        # Build test translucent binder.
        binder = TranslucentBinder(metadata={
            'title': self.base_metadata['title'],
            })

        metadata = self.base_metadata.copy()
        metadata.update({
            'title': "entrée",
            'derived_from_uri': 'http://cnx.org/contents/'
                                'dd68a67a-11f4-4140-a49f-b78e856e2262@1',
            'derived_from_title': "Taking Customers' Orders",
            })

        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))

        html = str(HTMLFormatter(binder))
        html = unescape(html)
        self.root = etree.fromstring(html.encode('utf-8'))

        self.assertIn(u'<title>タイトル</title>', html)

        lis = self.xpath('//xhtml:nav/xhtml:ol/xhtml:li')
        self.assertEqual(1, len(lis))
        self.assertEqual('ingress@draft.xhtml', lis[0][0].attrib['href'])
        self.assertEqual(u'entrée', lis[0][0].text)


@mock.patch('mimetypes.guess_extension', last_extension)
class SingleHTMLFormatterTestCase(unittest.TestCase):
    base_metadata = {
        'publishers': [],
        'created': '2016/03/04 17:05:20 -0500',
        'revised': '2013/03/05 09:35:24 -0500',
        'authors': [
            {'type': 'cnx-id',
             'name': 'Good Food',
             'id': 'yum'}],
        'editors': [],
        'copyright_holders': [],
        'illustrators': [],
        'subjects': ['Humanities'],
        'translators': [],
        'keywords': ['Food', 'デザート', 'Pudding'],
        'title': 'チョコレート',
        'license_text': 'CC-By 4.0',
        'license_url': 'http://creativecommons.org/licenses/by/4.0/',
        'summary': "<p>summary</p>",
        'version': 'draft',
        }

    maxDiff = None

    def setUp(self):
        from ..models import (TranslucentBinder, Binder, Document,
                              Resource, CompositeDocument)

        with open(os.path.join(TEST_DATA_DIR, '1x1.jpg'), 'rb') as f:
            jpg = Resource('1x1.jpg', io.BytesIO(f.read()), 'image/jpeg',
                           filename='small.jpg')

        metadata = self.base_metadata.copy()
        contents = io.BytesIO(u"""\
<h1>Chocolate Desserts</h1>
<p>List of desserts to try:</p>
<ul><li>Chocolate Orange Tart,</li>
    <li>Hot Mocha Puddings,</li>
    <li>Chocolate and Banana French Toast,</li>
    <li>Chocolate Truffles...</li>
</ul><img src="/resources/1x1.jpg" /><p>チョコレートデザート</p>
""".encode('utf-8'))
        self.chocolate = Document('chocolate', contents, metadata=metadata,
                                  resources=[jpg])

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Apple'
        contents = io.BytesIO(b"""\
<h1>Apple Desserts</h1>
<p>Here are some examples:</p>
<ul><li>Apple Crumble,</li>
    <li>Apfelstrudel,</li>
    <li>Caramel Apple,</li>
    <li>Apple Pie,</li>
    <li>Apple sauce...</li>
</ul>
""")
        self.apple = Document('apple', contents, metadata=metadata)

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Lemon'
        contents = io.BytesIO(b"""\
<h1>Lemon Desserts</h1>
<p>Yum! <img src="/resources/1x1.jpg" /></p>
<ul><li>Lemon &amp; Lime Crush,</li>
    <li>Lemon Drizzle Loaf,</li>
    <li>Lemon Cheesecake,</li>
    <li>Raspberry &amp; Lemon Polenta Cake...</li>
</ul>
""")
        self.lemon = Document('lemon', contents, metadata=metadata,
                              resources=[jpg])

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Citrus'
        self.citrus = TranslucentBinder([self.lemon], metadata=metadata)

        self.fruity = TranslucentBinder([self.apple, self.lemon, self.citrus],
                                        metadata={'title': 'Fruity'},
                                        title_overrides=[
                                            self.apple.metadata['title'],
                                            u'レモン', 'citrus'])

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        contents = io.BytesIO(b"""\
<h1>Extra Stuff</h1>
<p>This is a composite page.</p>
""")
        self.extra = CompositeDocument(
            'extra', contents, metadata=metadata)

        with open(os.path.join(TEST_DATA_DIR, 'cover.png'), 'rb') as f:
            cover_png = Resource(
                'cover.png', io.BytesIO(f.read()), 'image/png',
                filename='cover.png')

        self.desserts = Binder(
            'Desserts', [self.fruity, self.chocolate, self.extra],
            metadata={'title': 'Desserts'}, resources=[cover_png])

    def test_binder(self):
        from ..formatters import SingleHTMLFormatter

        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.xhtml')
        with open(page_path, 'r') as f:
            self.assertMultiLineEqual(
                f.read(), str(SingleHTMLFormatter(self.desserts)))

    def test_str_unicode_bytes(self):
        from ..formatters import SingleHTMLFormatter

        html = bytes(SingleHTMLFormatter(self.desserts))
        if IS_PY3:
            self.assertEqual(
                html, str(SingleHTMLFormatter(self.desserts)).encode('utf-8'))
        else:
            self.assertEqual(
                html, str(SingleHTMLFormatter(self.desserts)))
            self.assertEqual(
                html,
                unicode(SingleHTMLFormatter(self.desserts)).encode('utf-8'))
