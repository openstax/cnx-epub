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


class EPUBAdaptationTestCase(unittest.TestCase):
    maxDiff = None

    def make_package(self, file):
        from ..epub import Package
        return Package.from_file(file)

    def make_item(self, file, **kwargs):
        from ..epub import Item
        return Item.from_file(file, **kwargs)

    def test_to_binder(self):
        """Adapts a ``Package`` to a ``BinderItem``.
        Binders are native object representations of data,
        while the Package is merely a representation of EPUB structure.
        """
        # Easiest way to test this is using the ``model_to_tree`` utility
        # to analyze the structural equality.
        package_filepath = os.path.join(
            TEST_DATA_DIR, 'book',
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        package = self.make_package(package_filepath)
        expected_tree = {
            'id': '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6',
            'title': 'Book of Infinity',
            'shortId': u'mwkD0hPE@1.6',
            'contents': [
                {'id': 'subcol',
                 'shortId': None,
                 'title': 'Part One',
                 'contents': [
                     {'contents': [
                         {'id': 'e78d4f90-e078-49d2-beac-e95e8be70667@3',
                          'shortId': u'541PkOB4@3', 'title': 'Document One'}],
                      'id': 'subcol',
                      'shortId': None,
                      'title': 'Chapter One'},
                     {'id': 'subcol',
                      'shortId': None,
                      'title': 'Chapter Two',
                      'contents': [{'id': 'e78d4f90-e078-49d2-beac-e95e8be70667@3',
                                    'shortId': u'541PkOB4@3', 'title': 'Document One (again)'}],
                      }]},
                {'id': 'subcol',
                 'shortId': None,
                 'title': 'Part Two',
                 'contents': [
                     {'id': 'subcol',
                      'shortId': None,
                      'title': 'Chapter Three',
                      'contents': [
                          {'id': 'e78d4f90-e078-49d2-beac-e95e8be70667@3',
                            'shortId': u'541PkOB4@3', 'title': 'Document One (...and again)'}]
                      }]}]}

        from ..adapters import adapt_package
        binder = adapt_package(package)
        self.assertEqual(binder.id, '9b0903d2-13c4-4ebe-9ffe-1ee79db28482')
        self.assertEqual(binder.ident_hash,
                         '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6')
        self.assertEqual(len(binder.resources), 1)
        self.assertEqual(binder.resources[0].id, 'cover.png')
        with open(os.path.join(
                TEST_DATA_DIR, 'book', 'resources', 'cover.png'), 'rb') as f:
            expected_cover = f.read()
        with binder.resources[0].open() as f:
            binder_cover = f.read()
        self.assertEqual(expected_cover, binder_cover)

        # This checks the binder structure, and only taps at the documents.
        from ..models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)
        self.assertEqual(package.metadata['publication_message'], u'Nueva Versión')

    def test_to_translucent_binder(self):
        """Adapts a ``Package`` to a ``TranslucentBinder``.
        Translucent binders are native object representations of data,
        while the Package is merely a representation of EPUB structure.
        Furthermore, translucent binders are non-persistable objects,
        that contain the same behavior as binders, but lack metadata
        and material. They can be thought of as a protective sheath that
        is invisible, yet holds the contents together.
        """
        # Easiest way to test this is using the ``model_to_tree`` utility
        # to analyze the structural equality.
        package_filepath = os.path.join(
            TEST_DATA_DIR, 'loose-pages', "faux.opf")
        package = self.make_package(package_filepath)
        expected_tree = {
            'id': 'subcol',
            'shortId': None,
            'title': "Loose Pages",
            'contents': [{'id': None, 'shortId': None, 'title': 'Yummy'},
                         {'id': None, 'shortId': None, 'title': 'Da bomb'},
                         {'id': 'pointer@1', 'shortId': None, 'title': 'Pointer'}],
            }

        from ..adapters import adapt_package
        binder = adapt_package(package)

        # This checks the binder structure, and only taps at the documents.
        from ..models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)

    def test_to_document_wo_resources_o_references(self):
        """Adapts an ``Item`` to a ``DocumentItem``.
        Documents are native object representations of data,
        while the Item is merely a representation of an item
        in the EPUB structure.
        We are specifically testing for metadata parsing and
        resource discovery.
        """
        item_filepath = os.path.join(
            TEST_DATA_DIR, 'loose-pages', 'content',
            "fig-bush.xhtml")
        item = self.make_item(item_filepath, media_type='application/xhtml+xml')

        package = mock.Mock()
        # This would not typically be called outside the context of
        # a package, but in the case of a scoped test we use it.
        from ..adapters import adapt_item
        document = adapt_item(item, package)

        # Check the document metadata
        expected_metadata = {
            u'authors': [{u'id': u'https://github.com/marknewlyn',
                          u'name': u'Mark Horner',
                          u'type': u'github-id'},
                         {u'id': u'https://cnx.org/member_profile/sarblyth',
                          u'name': u'Sarah Blyth',
                          u'type': u'cnx-id'},
                         {u'id': u'https://example.org/profiles/charrose',
                          u'name': u'Charmaine St. Rose',
                          u'type': u'openstax-id'}],
            u'copyright_holders': [
                {u'id': u'https://cnx.org/member_profile/ream',
                 u'name': u'Ream',
                 u'type': u'cnx-id'}],
            u'created': u'2013/03/19 15:01:16 -0500',
            u'editors': [{u'id': None, u'name': u'I. M. Picky',
                          u'type': None}],
            u'illustrators': [{u'id': None, u'name': u'Francis Hablar',
                               u'type': None}],
            u'keywords': [u'South Africa'],
            u'license_text': u'CC-By 4.0',
            u'license_url': u'http://creativecommons.org/licenses/by/4.0/',
            u'publishers': [{u'id': None, u'name': u'Ream', u'type': None}],
            u'revised': u'2013/06/18 15:22:55 -0500',
            u'subjects': [u'Science and Mathematics'],
            u'summary': u'By the end of this section, you will be able to: \n        <ul xmlns="http://www.w3.org/1999/xhtml" xmlns:bib="http://bibtexml.sf.net/" xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute" xmlns:epub="http://www.idpf.org/2007/ops" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:lrmi="http://lrmi.net/the-specification" class="list">\n          <li class="item">Drive a car</li>\n          <li class="item">Purchase a watch</li>\n          <li class="item">Wear funny hats</li>\n          <li class="item">Eat cake</li>\n        </ul>',
            u'title': u'Document One of Infinity',
            u'translators': [{u'id': None, u'name': u'Francis Hablar',
                              u'type': None}],
            u'derived_from_uri': u'http://example.org/contents/id@ver',
            u'derived_from_title': u'Wild Grains and Warted Feet',
            u'cnx-archive-uri': None,
            u'cnx-archive-shortid': None,
            u'language': 'en',
            u'print_style': u'* print style *',
            u'version': None,
            }
        self.assertEqual(expected_metadata, document.metadata)

        # Check the document uri lookup
        uri = document.get_uri('cnx-archive')
        self.assertEqual(None, uri)

        # Check resource discovery.
        self.assertEqual([], document.references)

    def test_to_document_w_resources(self):
        """Adapts an ``Item`` to a ``DocumentItem``.
        Documents are native object representations of data,
        while the Item is merely a representation of an item
        in the EPUB structure.
        We are specifically testing for reference parsing and
        resource discovery.
        """
        content_filepath = os.path.join(
            TEST_DATA_DIR, 'loose-pages', 'content',
            "fig-bush.xhtml")
        file_pointer, item_filepath = tempfile.mkstemp()
        internal_uri = "../resources/openstax.png"
        with open(content_filepath, 'r') as fb:
            xml = etree.parse(fb)
            body = xml.xpath(
                '//xhtml:body',
                namespaces={'xhtml': "http://www.w3.org/1999/xhtml"})[0]
            elm = etree.SubElement(body, "img")
            elm.set('src', internal_uri)
        with open(item_filepath, 'wb') as fb:
            fb.write(etree.tostring(xml))
        item = self.make_item(item_filepath, media_type='application/xhtml+xml')

        package = mock.Mock()
        # This would not typically be called outside the context of
        # a package, but in the case of a scoped test we use it.

        resource_filepath = os.path.join(TEST_DATA_DIR, 'loose-pages',
                                         'resources', 'openstax.png')
        from ..models import Resource
        package.grab_by_name.side_effect = [
            self.make_item(resource_filepath, media_type='image/png'),
            ]
        from ..adapters import adapt_item
        document = adapt_item(item, package)

        # Check resource discovery.
        self.assertEqual([internal_uri],
                         [ref.uri for ref in document.references])
        # Check the resource was discovered.
        self.assertEqual(['openstax.png'],
                         [res.id for res in document.resources])
        # Check that the reference is bound to the resource
        ref = list(document.references)[0]
        res = list(document.resources)[0]
        self.assertEqual(ref._bound_model, res)

    def test_to_document_pointer(self):
        """Adapts an ``Item`` to a ``DocumentPointerItem``.
        Documents are native object representations of data,
        while the Item is merely a representation of an item
        in the EPUB structure.
        """
        item_filepath = os.path.join(
                TEST_DATA_DIR, 'loose-pages', 'content',
                'pointer.xhtml')

        package = mock.Mock()
        item = self.make_item(item_filepath, media_type='application/xhtml+xml')

        from ..adapters import adapt_item, DocumentPointerItem
        pointer = adapt_item(item, package)

        self.assertEqual(type(pointer), DocumentPointerItem)
        self.assertEqual(pointer.ident_hash, 'pointer@1')
        self.assertEqual(pointer.metadata['title'], 'Pointer')


@mock.patch('mimetypes.guess_extension', new=random_extension)
class ModelsToEPUBTestCase(unittest.TestCase):

    def test_loose_pages_wo_resources(self):
        """Create a publication EPUB from a loose set of pages."""
        from ..models import TranslucentBinder, Document
        binder = TranslucentBinder(metadata={'title': "Kraken"})

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

        # Build test documents
        metadata = base_metadata.copy()
        metadata.update({'title': "entrée"})
        binder.append(Document('ingress', io.BytesIO(b'<body><p>Hello.</p></body>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        binder.append(Document('egress', io.BytesIO(u'<body><p>hüvasti.</p></body>'.encode('utf-8')),
                               metadata=metadata))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_publication_epub
        with open(epub_filepath, 'wb') as epub_file:
            make_publication_epub(binder, 'krabs', '$.$', epub_file)

        # Verify the results.
        epub_path = tempfile.mkdtemp('-epub')
        self.addCleanup(shutil.rmtree, epub_path)
        from ..epub import unpack_epub
        unpack_epub(epub_filepath, epub_path)

        # Because a TranslucentBinder doesn't has an id of ``None``,
        # we uniquely create one using the object's hash.
        binder_hash = str(hash(binder))
        opf_filename = "{}.opf".format(binder_hash)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            [opf_filename, 'META-INF', 'contents', 'mimetype'],
            sorted(os.listdir(epub_path)))
        filenames = sorted(os.listdir(os.path.join(epub_path, 'contents')))
        self.assertEqual(
            [binder_hash, 'egress@draft', 'ingress@draft'],
            [os.path.splitext(filename)[0] for filename in filenames])
        self.assertEqual(
            ['application/xhtml+xml', 'application/xhtml+xml', 'application/xhtml+xml'],
            [mimetypes.guess_type(filename)[0] for filename in filenames])
        navdoc_filename, egress_filename, ingress_filename = filenames

        # Check the opf file
        with open(os.path.join(epub_path, opf_filename)) as f:
            opf = unescape(f.read())
        self.assertTrue(u'<dc:publisher>krabs</dc:publisher>' in opf)
        self.assertTrue(u'<meta property="publicationMessage">$.$</meta>' in opf)

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())
        expected_nav = (
            u'<nav id="toc"><ol><li cnx-archive-uri="ingress@draft">'
            u'<a href="{}">entrée</a>'
            u'</li><li cnx-archive-uri="egress@draft">'
            u'<a href="{}">egress</a>'
            u'</li></ol></nav>'.format(ingress_filename, egress_filename))
        self.assertIn(expected_nav, nav)

        # Check that translucent is set
        self.assertTrue('<span data-type="binding" data-value="translucent"' in nav)

        # Check the title and content
        self.assertTrue('<title>Kraken</title>' in nav)
        with open(os.path.join(epub_path, 'contents', egress_filename)) as f:
            egress = unescape(f.read())
        self.assertFalse('<div data-type="resources"' in egress)
        self.assertTrue('<title>egress</title>' in egress)
        self.assertTrue(u'<p>hüvasti.</p>' in egress)

        # Adapt epub back to documents and binders
        from cnxepub import EPUB
        from cnxepub.adapters import adapt_package
        from cnxepub.models import flatten_model
        epub = EPUB.from_file(epub_path)
        self.assertEqual(len(epub), 1)
        binder = adapt_package(epub[0])
        self.assertEqual(len(list(flatten_model(binder))), 3)

    def test_loose_pages_w_resources(self):
        """Create a publication EPUB from a loose set of pages."""
        from ..models import TranslucentBinder, Document, Resource
        binder = TranslucentBinder(metadata={'title': "Kraken"})

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
            'keywords': ['Bob', 'Sponge', 'Rock',
                         # Invalid xml in keywords
                         '</emphasis>horizontal line'],
            'title': "Goofy Goober Rock",
            'license_text': 'CC-By 4.0',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'summary': "<p>summary</p>",
            'version': 'draft',
            }

        # Build test documents
        metadata = base_metadata.copy()
        metadata.update({'title': "entrée"})
        binder.append(Document('ingress', io.BytesIO(
            b'<body><p><a href="http://cnx.org/">Hello.</a><a id="nohref">Goodbye</a></p></body>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        with open(os.path.join(TEST_DATA_DIR, '1x1.jpg'), 'rb') as f:
            jpg = Resource('1x1.jpg', io.BytesIO(f.read()), 'image/jpeg',
                           filename='1x1.jpg')
        binder.append(Document('egress', io.BytesIO(
            u'<body><p><img src="1x1.jpg" />hüvasti.</p><p><img longdesc="1x1.jpg" src="1x1.jpg" />hüvastilongdesc.</p></body>'.encode('utf-8')),
                               metadata=metadata,
                               resources=[jpg]))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_publication_epub
        with open(epub_filepath, 'wb') as epub_file:
            make_publication_epub(binder, 'krabs', '$.$', epub_file)

        # Verify the results.
        epub_path = tempfile.mkdtemp('-epub')
        self.addCleanup(shutil.rmtree, epub_path)
        from ..epub import unpack_epub
        unpack_epub(epub_filepath, epub_path)

        # Because a TranslucentBinder doesn't has an id of ``None``,
        # we uniquely create one using the object's hash.
        binder_hash = str(hash(binder))
        opf_filename = "{}.opf".format(binder_hash)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            [opf_filename, 'META-INF', 'contents', 'mimetype', 'resources'],
            sorted(os.listdir(epub_path)))
        filenames = sorted(os.listdir(os.path.join(epub_path, 'contents')))
        self.assertEqual(
            [binder_hash, 'egress@draft', 'ingress@draft'],
            [os.path.splitext(filename)[0] for filename in filenames])
        self.assertEqual(
            ['application/xhtml+xml', 'application/xhtml+xml', 'application/xhtml+xml'],
            [mimetypes.guess_type(filename)[0] for filename in filenames])
        self.assertEqual(os.listdir(os.path.join(epub_path, 'resources')),
                         ['1x1.jpg'])
        navdoc_filename, egress_filename, ingress_filename = filenames

        # Check the opf file
        with open(os.path.join(epub_path, opf_filename)) as f:
            opf = unescape(f.read())
        self.assertTrue(u'<dc:publisher>krabs</dc:publisher>' in opf)
        self.assertTrue(u'<meta property="publicationMessage">$.$</meta>' in opf)

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())
        expected_nav = (
            u'<nav id="toc"><ol><li cnx-archive-uri="ingress@draft">'
            u'<a href="{}">entrée</a>'
            u'</li><li cnx-archive-uri="egress@draft">'
            u'<a href="{}">egress</a>'
            u'</li></ol></nav>'.format(ingress_filename, egress_filename))
        self.assertIn(expected_nav, nav)

        # Check that translucent is set
        self.assertTrue('<span data-type="binding" data-value="translucent"' in nav)

        # Check the title and content
        self.assertTrue('<title>Kraken</title>' in nav)
        with open(os.path.join(epub_path, 'contents', egress_filename)) as f:
            egress = unescape(f.read())
        self.assertTrue('<title>egress</title>' in egress)
        self.assertFalse('<span data-type="cnx-archive-uri"' in egress)
        self.assertTrue(re.search(
            '<div data-type="resources"[^>]*>\s*<ul>\s*'
            '<li>\s*<a href="1x1.jpg">1x1.jpg</a>\s*</li>\s*</ul>\s*</div>', egress))
        self.assertTrue(u'<p><img src="../resources/1x1.jpg"/>hüvasti.</p>' in egress)
        self.assertTrue(u'<p><img longdesc="../resources/1x1.jpg" src="../resources/1x1.jpg"/>hüvastilongdesc.</p>' in egress)

        # Adapt epub back to documents and binders
        from cnxepub import EPUB
        from cnxepub.adapters import adapt_package
        from cnxepub.models import flatten_model
        epub = EPUB.from_file(epub_path)
        self.assertEqual(len(epub), 1)
        binder = adapt_package(epub[0])
        self.assertEqual(len(list(flatten_model(binder))), 3)

        document = binder[0]
        self.assertEqual(document.metadata['keywords'],
                         base_metadata['keywords'])

    def test_binder(self):
        """Create an EPUB from a binder with a few documents."""
        from ..models import Binder, Document, DocumentPointer, Resource
        binder_name = 'rock'
        with open(os.path.join(TEST_DATA_DIR, 'cover.png'), 'rb') as f:
            cover = Resource('cover.png', io.BytesIO(f.read()), 'image/png',
                             filename='cover.png')
        binder = Binder(binder_name, metadata={'title': "Kraken (Nueva Versión)",
                                               'license_url': "http://my.license"},
                        resources=[cover])

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

        # Build test documents
        metadata = base_metadata.copy()
        metadata.update({
            'title': "entrée",
            'derived_from_uri': 'http://cnx.org/contents/dd68a67a-11f4-4140-a49f-b78e856e2262@1',
            'derived_from_title': "Taking Customers' Orders",
            })
        binder.append(Document('ingress', io.BytesIO(b'<body><p>Hello.</p></body>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress",
                         'cnx-archive-uri': 'e78d4f90-e078-49d2-beac-e95e8be70667'})
        binder.append(Document('egress', io.BytesIO(u'<body><p>hüvasti.</p></body>'.encode('utf-8')),
                               metadata=metadata))
        binder.append(DocumentPointer('pointer@1', {
            'title': 'Pointer',
            'cnx-archive-uri': 'pointer@1',
            'url': 'http://cnx.org/contents/pointer@1'}))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_publication_epub
        with open(epub_filepath, 'wb') as epub_file:
            make_publication_epub(binder, 'krabs', '$.$', epub_file)

        # Verify the results.
        epub_path = tempfile.mkdtemp('-epub')
        self.addCleanup(shutil.rmtree, epub_path)
        from ..epub import unpack_epub
        unpack_epub(epub_filepath, epub_path)

        opf_filename = "{}.opf".format(binder_name)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            ['META-INF', 'contents', 'mimetype', 'resources', opf_filename],
            sorted(os.listdir(epub_path)))

        # Check resources
        self.assertEqual(['cover.png'],
                         os.listdir(os.path.join(epub_path, 'resources')))
        with open(os.path.join(epub_path, 'resources', 'cover.png'), 'rb') as f:
            epub_cover = f.read()
        with open(os.path.join(TEST_DATA_DIR, 'cover.png'), 'rb') as f:
            expected_cover = f.read()
        self.assertEqual(expected_cover, epub_cover)

        filenames = sorted(os.listdir(os.path.join(epub_path, 'contents')))
        self.assertEqual(
            ['egress@draft', 'ingress@draft', 'pointer@1', binder_name],
            [os.path.splitext(filename)[0] for filename in filenames])
        self.assertEqual(
            ['application/xhtml+xml', 'application/xhtml+xml',
                'application/xhtml+xml', 'application/xhtml+xml'],
            [mimetypes.guess_type(filename)[0] for filename in filenames])
        egress_filename, ingress_filename, pointer_filename, navdoc_filename = filenames

        # Check the opf file
        with open(os.path.join(epub_path, opf_filename)) as f:
            opf = unescape(f.read())
        self.assertTrue(u'<dc:publisher>krabs</dc:publisher>' in opf)
        self.assertTrue(u'<meta property="publicationMessage">$.$</meta>' in opf)
        self.assertTrue(u'href="resources/cover.png"' in opf)

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())

        expected_nav = (
            u'<nav id="toc"><ol><li cnx-archive-uri="ingress@draft">'
            u'<a href="{}">entrée</a>'
            u'</li><li cnx-archive-uri="egress@draft">'
            u'<a href="{}">egress</a>'
            u'</li><li cnx-archive-uri="pointer@1">'
            u'<a href="{}">Pointer</a>'
            u'</li></ol></nav>'.format(ingress_filename, egress_filename,
                                       pointer_filename))
        self.assertTrue(expected_nav in nav)

        # Check the resources
        self.assertTrue(u'<a href="cover.png">cover.png</a>' in nav)

        # Check that translucent is not set
        self.assertFalse('<span data-type="binding" data-value="translucent"' in nav)

        # Check the title and content
        self.assertTrue(u'<title>Kraken (Nueva Versión)</title>' in nav)
        with open(os.path.join(epub_path, 'contents', egress_filename)) as f:
            egress = unescape(f.read())
        with open(os.path.join(epub_path, 'contents', ingress_filename)) as f:
            ingress = unescape(f.read())
        self.assertTrue('<title>egress</title>' in egress)
        self.assertTrue('<span data-type="cnx-archive-uri" '
                        'data-value="e78d4f90-e078-49d2-beac-e95e8be70667"' in egress)
        self.assertTrue(u'<p>hüvasti.</p>' in egress)
        self.assertFalse('Derived from:' in egress)
        self.assertTrue('Derived from:' in ingress)
        self.assertTrue('http://cnx.org/contents/dd68a67a-11f4-4140-a49f-b78e856e2262@1' in ingress)
        self.assertTrue("Taking Customers' Orders" in ingress)

        # Check the content of the document pointer file
        with open(os.path.join(epub_path, 'contents', pointer_filename)) as f:
            pointer = unescape(f.read())
        self.assertTrue('<title>Pointer</title>' in pointer)
        self.assertTrue('<span data-type="document" data-value="pointer"' in pointer)
        self.assertTrue('<span data-type="cnx-archive-uri" '
                        'data-value="pointer@1"' in pointer)
        self.assertTrue('<a href="http://cnx.org/contents/pointer@1">here</a>' in pointer)

        # Adapt epub back to documents and binders
        from cnxepub import EPUB
        from cnxepub.adapters import adapt_package
        from cnxepub.models import flatten_model
        epub = EPUB.from_file(epub_path)
        self.assertEqual(len(epub), 1)
        binder = adapt_package(epub[0])
        self.assertEqual(len(list(flatten_model(binder))), 4)


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
        u'print_style': None,
        u'cnx-archive-uri': None,
        u'cnx-archive-shortid': None,
        u'derived_from_title': None,
        u'derived_from_uri': None,
        u'version': None,
        }

    def test_from_formatter_to_adapter(self):
        from ..adapters import adapt_single_html
        from ..formatters import SingleHTMLFormatter
        from ..models import Binder, Document, DocumentPointer

        random.seed(1)
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
    </body>
</html>'''), metadata=metadata))
        binder.append(DocumentPointer('content-ident-hash', metadata={
            'title': 'Test Document Pointer',
            'url': 'https://cnx.org/'}))

        single_html = str(SingleHTMLFormatter(binder))
        adapted_binder = adapt_single_html(single_html)

        random.seed(1)
        self.assertEqual(len(adapted_binder), len(binder))
        self.assertEqual(adapted_binder[0].id, 'apple-pie')
        self.assertEqual(adapted_binder[1].id, 'lemon-pie')
        self.assertEqual(adapted_binder[0].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="apple-pie"><p id="{}">Apple Pie</p>
  </div></body>'''.format(random.randint(0, 100000)))
        self.assertEqual(adapted_binder[1].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="lemon-pie"><h1>Lemon Pie</h1>\n        \n        <p id="{}">Yum.</p>\n    \n    \n  </div></body>'''.format(random.randint(0, 100000)))
        self.assertEqual(adapted_binder[2].id, 'content-ident-hash')
        self.assertEqual(adapted_binder[2].metadata['title'],
                         'Test Document Pointer')
        self.assertEqual(adapted_binder[2].content.decode('utf-8'), '''\
<body xmlns="http://www.w3.org/1999/xhtml"><div data-type="page" id="content-\
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
                            'id': 'apple@1.3',
                            'title': 'Apple'
                        },
                        {
                            'shortId': None,
                            'id': 'lemon@1.3',
                            'title': u'<span>1.1</span> <span>|</span> <span>レモン</span>'
                        },

                        {
                            'shortId': 'sfE7YYyV@1.3',
                            'id': 'b1f13b61-8c95-5fbe-9112-46400b6dc8de@1.3',
                            'contents': [
                                {
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
        self.assertEqual('ec84e75d-9973-41f1-ab9d-1a3ebaef87e2', fruity.metadata['id'])
        self.assertEqual('frt', fruity.metadata['shortId'])
        self.assertEqual('Fruity', desserts.get_title_for_node(fruity))

        apple = fruity[0]
        self.assertEqual('Document', apple.__class__.__name__)
        metadata = self.base_metadata.copy()
        metadata['title'] = 'Apple'
        metadata['version'] = '1.3'
        apple_metadata = apple.metadata.copy()
        summary = etree.fromstring(apple_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, apple_metadata)
        self.assertIn(b'<p id="74606">'
                      b'<a href="/contents/lemon">Link to lemon</a>. '
                      b'Here are some examples:</p>',
                      apple.content)
        self.assertEqual('Apple', fruity.get_title_for_node(apple))

        lemon = fruity[1]
        self.assertEqual('Document', lemon.__class__.__name__)
        metadata = self.base_metadata.copy()
        metadata['title'] = 'Lemon'
        metadata['version'] = '1.3'
        lemon_metadata = lemon.metadata.copy()
        summary = etree.fromstring(lemon_metadata.pop('summary'))
        self.assertEqual('{http://www.w3.org/1999/xhtml}p', summary.tag)
        self.assertEqual('summary', summary.text)
        self.assertEqual(metadata, lemon_metadata)
        self.assertIn(b'<p id="8271">Yum! <img src="/resources/1x1.jpg" '
                      b'id="33432"/></p>', lemon.content)
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
        self.assertEqual(metadata, chocolate_metadata)
        self.assertIn(b'<p id="12302"><a href="#list">List</a> of',
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
        self.assertEqual(metadata, extra_metadata)
        self.assertIn(b'<p id="56723">Here is a <a href="/contents/chocolate'
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

        from ..adapters import AdaptationError
        with self.assertRaises(AdaptationError) as caught_exception:
            desserts = adapt_single_html(html)

    def test_unknown_data_type(self):
        """Throw error if unknown data-type in HTML"""
        page_path = os.path.join(TEST_DATA_DIR, 'desserts-single-page-bad-type.xhtml')
        from ..adapters import adapt_single_html
        from ..models import model_to_tree

        with open(page_path, 'r') as f:
            html = f.read()

        from ..adapters import AdaptationError
        with self.assertRaises(AdaptationError) as caught_exception:
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
        self.assertIn(b'<p id="12345"><a href="/contents/chocolate">',
                      apple.content)
