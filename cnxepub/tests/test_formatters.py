# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import codecs
import io
import json
import mimetypes
import os
import subprocess
import sys
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from ..testing import (TEST_DATA_DIR, unescape,
                       _get_memcache_client, IS_MEMCACHE_ENABLED)
from ..formatters import exercise_callback_factory

here = os.path.abspath(os.path.dirname(__file__))

IS_PY3 = sys.version_info.major == 3

XMLPP_DIR = os.path.join(here, 'utils')


def xmlpp(input_):
    """Pretty Print XML"""
    proc = subprocess.Popen(['./xmlpp.pl', '-sSten'],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=XMLPP_DIR)
    output, _ = proc.communicate(input_)
    return output


def _c14n(val):
    ov = io.BytesIO()
    ET = etree.fromstring(str(val)).getroottree()
    ET.write_c14n(ov)
    return ov.getvalue().decode('utf-8')


def last_extension(*args, **kwargs):
    # Always return the last value of sorted mimetypes.guess_all_extensions
    exts = mimetypes.guess_all_extensions(*args, **kwargs)
    return sorted(exts)[-1]


EXERCISE_JSON_HTML = {
   "items": [
      {
         "uid": "93@3",
         "group_uuid": "e071207a-9d26-4cff-bbe9-9060d3d13ca6",
         "copyright_holders": [
            {
               "user_id": 2,
               "name": "Rice University"
            }
         ],
         "uuid": "8fa80526-0720-4a98-99c8-5d6113482424",
         "authors": [
            {
               "user_id": 1,
               "name": "OpenStax"
            }
         ],
         "published_at": "2016-09-16T17:40:20.497Z",
         "number": 93,
         "editors": [],
         "is_vocab": False,
         "stimulus_html": "",
         "questions": [
            {
               "stimulus_html": "",
               "formats": [
                  "free-response",
                  "multiple-choice"
               ],
               "hints": [],
               "id": 63062,
               "is_answer_order_important": True,
               "answers": [
                  {
                     "id": 259956,
                     "content_html": "monomers",
                     "correctness": "0.0"
                  },
                  {
                     "content_html": "polymers (<span data-math='retry' />)",
                     "id": 259957,
                     "correctness": "1.0"

                  },
                  {
                     "id": 259958,
                     "content_html": "carbohydrates only (<span data-math='' />)",
                     "correctness": "0.0"
                  },
                  {
                     "content_html": "water only (<span data-math='\\text{H}_2\\text{O}'>\\text{H}_2\\text{O}</span>)",
                     "id": 259959,
                     "correctness": "0.0"
                  },
                  {
                     "content_html": "polymer and water (<div data-math='\\text{H}_2\\text{O}'>\\text{H}_2\\text{O}</div>)",
                     "id": 259959,
                     "correctness": "1.0"
                  }
               ],
               "combo_choices": [],
               "stem_html": "Dehydration <img href='none'> synthesis leads to the formation of what?"
            }
         ],
         "tags": [
            "apbio",
            "inbook-yes",
            "ost-chapter-review",
            "review",
            "apbio-ch03",
            "apbio-ch03-s01",
            "apbio-ch03-s01-lo01",
            "apbio-ch03-ex002",
            "dok:1",
            "blooms:1",
            "time:short",
            "book:stax-bio",
            "context-cnxmod:ea44b8fa-e7a2-4360-ad34-ac081bcf104f",
            "exid:apbio-ch03-ex002",
            "context-cnxmod:85d6c500-9860-42e8-853a-e6940a50224f",
            "book:stax-apbio",
            "filter-type:import:hs",
            "type:conceptual-or-recall"
         ],
         "derived_from": [],
         "version": 3
      }
   ],
   "total_count": 1
}

EXERCISE_JSON = {
   "items": [
      {
         "uid": "93@3",
         "group_uuid": "e071207a-9d26-4cff-bbe9-9060d3d13ca6",
         "copyright_holders": [
            {
               "user_id": 2,
               "name": "Rice University"
            }
         ],
         "uuid": "8fa80526-0720-4a98-99c8-5d6113482424",
         "authors": [
            {
               "user_id": 1,
               "name": "OpenStax"
            }
         ],
         "published_at": "2016-09-16T17:40:20.497Z",
         "number": 93,
         "editors": [],
         "is_vocab": False,
         "stimulus_html": "",
         "questions": [
            {
               "stimulus_html": "",
               "formats": [
                  "free-response",
                  "multiple-choice"
               ],
               "hints": [],
               "id": 63062,
               "is_answer_order_important": True,
               "answers": [
                  {
                     "id": 259956,
                     "content_html": "monomers"
                  },
                  {
                     "content_html": "polymers",
                     "id": 259957
                  },
                  {
                     "id": 259958,
                     "content_html": "carbohydrates only"
                  },
                  {
                     "content_html": "water only",
                     "id": 259959
                  }
               ],
               "combo_choices": [],
               "stem_html": "Dehydration <img href='none'/> synthesis leads to the formation of what?"
            }
         ],
         "tags": [
            "apbio",
            "inbook-yes",
            "ost-chapter-review",
            "review",
            "apbio-ch03",
            "apbio-ch03-s01",
            "apbio-ch03-s01-lo01",
            "apbio-ch03-ex002",
            "dok:1",
            "blooms:1",
            "time:short",
            "book:stax-bio",
            "context-cnxmod:ea44b8fa-e7a2-4360-ad34-ac081bcf104f",
            "exid:apbio-ch03-ex002",
            "context-cnxmod:85d6c500-9860-42e8-853a-e6940a50224f",
            "book:stax-apbio",
            "filter-type:import:hs",
            "type:conceptual-or-recall"
         ],
         "derived_from": [],
         "version": 3
      }
   ],
   "total_count": 1
}

BAD_EQUATION_JSON = {
    "error": "E_VALIDATION",
    "status": 400,
    "summary": "1 attribute is invalid",
    "model": "Equation",
    "invalidAttributes": {
        "math": [{"rule": "required",
                  "message": "\"required\" validation rule failed for input: ''\nSpecifically, it threw an error.  Details:\n undefined"}]
        }
    }


EQUATION_JSON = {
    "updatedAt": "2016-10-31T16:06:44.413Z",
    "cloudUrl": "https://mathmlcloud.cnx.org:1337/equation/58176c14d08360010084f48c",
    "mathType": "TeX",
    "math": "\\text{H}_2\\text{O}",
    "components": [
        {
            "format": "mml",
            "equation": "58176c14d08360010084f48c",
            "source": '<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">\n  <msub>\n    <mtext>H</mtext>\n    <mn>2</mn>\n  </msub>\n  <mtext>O</mtext>\n</math>',
            "updatedAt": "2016-10-31T16:06:44.477Z",
            "id": "58176c14d08360010084f48d",
            "createdAt": "2016-10-31T16:06:44.477Z"
        }
    ],
    "submittedBy": None,
    "ip_address": "::ffff:10.64.71.226",
    "id": "58176c14d08360010084f48c",
    "createdAt": "2016-10-31T16:06:44.413Z"
}


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.text = json.dumps(json_data)
        self.status_code = status_code

    def json(self):
        return self.json_data


def mocked_requests_get(*args, **kwargs):
    # Replace requests.get with this mock
    # modified from http://stackoverflow.com/a/28507806/5430

    if args[0] == 'https://exercises.openstax.org/api/exercises?q=tag:apbio-ch03-ex002':
        if 'headers' in kwargs:
            assert kwargs['headers'] == {'Authorization': 'Bearer somesortoftoken'}
            return MockResponse(EXERCISE_JSON_HTML, 200)
        return MockResponse(EXERCISE_JSON, 200)

    else:
        return MockResponse({"total_count": 0, "items": []}, 200)


def mocked_requests_post(*args, **kwargs):
    if args[0].startswith('http://mathmlcloud.cnx.org/equation'):
        if args[1]['math'] == b'\\text{H}_2\\text{O}':
            return MockResponse(EQUATION_JSON, 200)
        elif args[1]['math'] == b'retry':
            return MockResponse('{}', 200)
        elif args[1]['math'] == b'':
            return MockResponse(BAD_EQUATION_JSON, 400)
        else:
            return MockResponse('', 500)
    return MockResponse({}, 404)


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
            'language': 'en'
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

        document = Document('title', io.BytesIO(b'<p>contents</p>'),
                            metadata={'summary': '<p>résumé</p>'})
        html = str(DocumentSummaryFormatter(document))
        self.assertEqual('<p>résumé</p>', html)

    def test_summary_w_just_text(self):
        from ..formatters import DocumentSummaryFormatter
        from ..models import Document

        document = Document('title', io.BytesIO(b'<p>contents</p>'),
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

        document = Document('title', io.BytesIO(b'<p>contents</p>'),
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
        'language': 'en'
        }

    maxDiff = None

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
            'license_url': self.base_metadata['license_url'],
            'license_text': self.base_metadata['license_text'],
            'language': self.base_metadata['language']
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

    def test_document_auto_generate_ids(self):
        import random

        from ..models import Document
        from ..formatters import HTMLFormatter

        random.seed(1)
        content = """<div>\
<div class="title" id="title">Preface</div>
<p class="para" id="my-id">This thing and <em>that</em> thing.</p>
<p class="para"><a href="#title">Link</a> to title</p></div>"""
        page_one_id = 'fa21215a-91b5-424a-9fbd-5c451f309b87'

        expected_content = """\
<div class="title" id="auto_{id}_title">Preface</div>

<p class="para" id="auto_{id}_my-id">This thing and <em>that</em> thing.</p>

<p class="para" id="auto_{id}_{n}"><a href="#auto_{id}_title">Link</a> to title</p>\
""".format(id=page_one_id, n=random.randint(0, 100000))

        random.seed(1)
        document = Document(page_one_id, content)
        formatted = str(HTMLFormatter(document, generate_ids=True))
        self.assertIn(expected_content, formatted)


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
<div>
<h1>Chocolate Desserts</h1>
<p><a href="#list">List</a> of desserts to try:</p>
<div data-type="list" id="list"><ul><li>Chocolate Orange Tart,</li>
    <li>Hot Mocha Puddings,</li>
    <li>Chocolate and Banana French Toast,</li>
    <li>Chocolate Truffles...</li>
</ul></div><img src="/resources/1x1.jpg" /><p>チョコレートデザート</p>
</div>
""".encode('utf-8'))
        self.chocolate = Document('chocolate', contents, metadata=metadata,
                                  resources=[jpg])

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Apple'
        contents = io.BytesIO(b"""\
<div>
<h1>Apple Desserts</h1>
<p><a href="/contents/lemon">Link to lemon</a>. Here are some examples:</p>
<ul><li id="auto_apple_13436">Apple Crumble,</li>
    <li>Apfelstrudel,</li>
    <li id="auto_apple_17611">Caramel Apple,</li>
    <li>Apple Pie,</li>
    <li>Apple sauce...</li>
</ul>
</div>
""")
        self.apple = Document('apple', contents, metadata=metadata)

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Lemon'
        contents = io.BytesIO(b"""\
<body class="fruity">
<h1>Lemon Desserts</h1>
<p>Yum! <img src="/resources/1x1.jpg" /></p>
<div data-type="exercise">
    <a href="#ost/api/ex/apbio-ch03-ex002">[link]</a>
</div>

<div data-type="exercise">
    <p>
    <a href="#ost/api/ex/nosuchtag">[link]</a>
    </p>
</div>
<ul><li>Lemon &amp; Lime Crush,</li>
    <li>Lemon Drizzle Loaf,</li>
    <li>Lemon Cheesecake,</li>
    <li>Raspberry &amp; Lemon Polenta Cake...</li>
</ul>
</body>
""")
        self.lemon = Document('lemon', contents, metadata=metadata,
                              resources=[jpg])

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Citrus'
        self.citrus = TranslucentBinder([self.lemon], metadata=metadata)

        title_overrides = [
            self.apple.metadata['title'],
            u'<span>1.1</span> <span>|</span> <span>レモン</span>',
            '<span>Chapter</span> <span>2</span> <span>citrus</span>']
        self.fruity = Binder('ec84e75d-9973-41f1-ab9d-1a3ebaef87e2', [self.apple, self.lemon, self.citrus],
                             metadata={'title': 'Fruity',
                                       'cnx-archive-uri': 'ec84e75d-9973-41f1-ab9d-1a3ebaef87e2',
                                       'cnx-archive-shortid': 'frt',
                                       'license_text': 'CC-By 4.0',
                                       'license_url': 'http://creativecommons.org/licenses/by/4.0/',
                                       },
                             title_overrides=title_overrides)

        metadata = self.base_metadata.copy()
        metadata['title'] = 'Extra Stuff'
        contents = io.BytesIO(b"""\
<div>
<h1>Extra Stuff</h1>
<p>This is a composite page.</p>
<p>Here is a <a href="#auto_chocolate_list">link</a> to another document.</p>
</div>
""")
        self.extra = CompositeDocument(
            'extra', contents, metadata=metadata)

        with open(os.path.join(TEST_DATA_DIR, 'cover.png'), 'rb') as f:
            cover_png = Resource(
                'cover.png', io.BytesIO(f.read()), 'image/png',
                filename='cover.png')

        self.desserts = Binder(
            'Desserts', [self.fruity, self.chocolate, self.extra],
            metadata={'title': 'Desserts',
                      'license_url': 'http://creativecommons.org/licenses/by/4.0/',
                      'license_text': 'CC-By 4.0',
                      'cnx-archive-uri': '00000000-0000-0000-0000-000000000000@1.3',
                      'language': 'en'},
            resources=[cover_png])

    def test_binder(self):
        import random

        from ..formatters import SingleHTMLFormatter

        random.seed(1)
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page.xhtml')
        if not IS_PY3:
            page_path = page_path.replace('.xhtml', '-py2.xhtml')

        with open(page_path, 'r') as f:
            expected_content = f.read()

        actual = str(SingleHTMLFormatter(self.desserts))
        out_path = os.path.join(TEST_DATA_DIR,
                                'desserts-single-page-actual.xhtml')
        if not IS_PY3:
            out_path = out_path.replace('.xhtml', '-py2.xhtml')

        with open(out_path, 'w') as out:
            out.write(actual)
        self.assertMultiLineEqual(expected_content, actual)
        # Placed after the assert, so only called if success:
        os.remove(out_path)

    def test_str_unicode_bytes(self):
        import random

        from ..formatters import SingleHTMLFormatter

        random.seed(1)
        html = bytes(SingleHTMLFormatter(self.desserts))
        if IS_PY3:
            random.seed(1)
            self.assertMultiLineEqual(
                html.decode('utf-8'), str(SingleHTMLFormatter(self.desserts)))
        else:
            random.seed(1)
            self.assertMultiLineEqual(
                html, str(SingleHTMLFormatter(self.desserts)))
            random.seed(1)
            self.assertMultiLineEqual(
                html,
                unicode(SingleHTMLFormatter(self.desserts)).encode('utf-8'))

    @mock.patch('requests.get', mocked_requests_get)
    def test_includes_callback(self):
        import random

        from ..formatters import SingleHTMLFormatter

        def _upcase_text(elem):
            if elem.text:
                elem.text = elem.text.upper()

        random.seed(1)
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-includes.xhtml')
        if not IS_PY3:
            page_path = page_path.replace('.xhtml', '-py2.xhtml')

        with codecs.open(page_path, 'r', encoding='utf-8') as f:
            expected_content = f.read()

        exercise_url = \
            'https://%s/api/exercises?q=tag:{itemCode}' % ('exercises.openstax.org')
        exercise_match = '#ost/api/ex/'

        if IS_MEMCACHE_ENABLED:
            mc_client = _get_memcache_client()
        else:
            mc_client = None

        includes = [exercise_callback_factory(exercise_match,
                                              exercise_url,
                                              mc_client),
                    ('//xhtml:a', _upcase_text)]

        actual = SingleHTMLFormatter(self.desserts,
                                     includes=includes)
        out_path = os.path.join(TEST_DATA_DIR, 'desserts-includes-actual.xhtml')
        if not IS_PY3:
            out_path = out_path.replace('.xhtml', '-py2.xhtml')
            with open(out_path, 'w') as out:
                out.write(xmlpp(unicode(actual).encode('utf-8')))
            with codecs.open(out_path, 'r', encoding='utf-8') as f:
                actual_content = f.read()
            self.assertEqual(xmlpp(expected_content.encode('utf-8')).split(b'\n'),
                             xmlpp(actual_content.encode('utf-8')).split(b'\n'))
        else:
            with open(out_path, 'w') as out:
                out.write(str(actual))
                self.assertMultiLineEqual(expected_content, str(actual))
        # After assert, so won't clean up if test fails
        os.remove(out_path)

    @mock.patch('requests.post', mocked_requests_post)
    @mock.patch('requests.get', mocked_requests_get)
    def test_includes_token_callback(self):
        import random

        from ..formatters import SingleHTMLFormatter

        def _upcase_text(elem):
            if elem.text:
                elem.text = elem.text.upper()

        random.seed(1)
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-includes-token.xhtml')
        if not IS_PY3:
            page_path = page_path.replace('.xhtml', '-py2.xhtml')

        with codecs.open(page_path, 'r', encoding='utf-8') as f:
            expected_content = f.read()

        exercise_url = \
            'https://%s/api/exercises?q=tag:{itemCode}' % ('exercises.openstax.org')
        exercise_match = '#ost/api/ex/'
        exercise_token = 'somesortoftoken'
        mathml_url = 'http://mathmlcloud.cnx.org/equation'
        if IS_MEMCACHE_ENABLED:
            mc_client = _get_memcache_client()
        else:
            mc_client = None

        includes = [exercise_callback_factory(exercise_match,
                                              exercise_url,
                                              mc_client,
                                              exercise_token,
                                              mathml_url),
                    ('//xhtml:a', _upcase_text)]

        actual = SingleHTMLFormatter(self.desserts,
                                     includes=includes)
        out_path = os.path.join(TEST_DATA_DIR,
                                'desserts-includes-token-actual.xhtml')
        if not IS_PY3:
            out_path = out_path.replace('.xhtml', '-py2.xhtml')
            with open(out_path, 'w') as out:
                out.write(xmlpp(unicode(actual).encode('utf-8')))
            with codecs.open(out_path, 'r', encoding='utf-8') as f:
                actual_content = f.read()
            self.assertEqual(xmlpp(expected_content.encode('utf-8')).split(b'\n'),
                             xmlpp(actual_content.encode('utf-8')).split(b'\n'))
        else:
            with open(out_path, 'w') as out:
                out.write(str(actual))
            self.assertMultiLineEqual(expected_content, str(actual))

        # After assert, so won't clean up if test fails
        os.remove(out_path)
