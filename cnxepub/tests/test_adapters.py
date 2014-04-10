# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
try:
    import html.parser as HTMLParser
except:
    import HTMLParser
import os
import io
import tempfile
import shutil
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


def unescape(html):
    p = HTMLParser.HTMLParser()
    return p.unescape(html)


class AdaptationTestCase(unittest.TestCase):

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
            'id': None,
            'title': 'Book of Infinity',
            'contents': [
                {'id': 'subcol',
                 'title': 'Part One',
                 'contents': [
                     {
                      'contents': [
                          {'id': None, 'title': 'Document One'}],
                             'id': 'subcol',
                             'title': 'Chapter One'},
                     {'id': 'subcol',
                      'title': 'Chapter Two',
                      'contents': [{'id': None,
                                    'title': 'Document One (again)'}],
                      }]},
                {'id': 'subcol',
                 'title': 'Part Two',
                 'contents': [
                     {'id': 'subcol',
                      'title': 'Chapter Three',
                      'contents': [
                          {'id': None,
                           'title': 'Document One (...and again)'}]
                      }]}]}

        from ..adapters import adapt_package
        binder = adapt_package(package)

        # This checks the binder structure, and only taps at the documents.
        from ..models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)

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
            'title': "Loose Pages",
            'contents': [{'id': None, 'title': 'Yummy'},
                         {'id': None, 'title': 'Da bomb'}],
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
            'publishers': [],
            'created': '2013/03/19 15:01:16 -0500',
            'revised': '2013/06/18 15:22:55 -0500',
            'authors': [
                {'type': 'github-id',
                 'name': 'Mark Horner',
                 'id': 'https://github.com/marknewlyn'},
                {'type': 'cnx-id',
                 'name': 'Sarah Blyth',
                 'id': 'https://cnx.org/member_profile/sarblyth'},
                {'type': 'openstax-id',
                 'name': 'Charmaine St. Rose',
                 'id': 'https://example.org/profiles/charrose'}],
            'editors': [], 'copyright_holders': [],
            'illustrators': [],
            'subjects': ['Science and Mathematics'],
            'translators': [],
            'keywords': ['South Africa'],
            'title': 'Document One of Infinity',
            'license_text': 'CC-By 4.0',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'summary': '<div xmlns="http://www.w3.org/1999/xhtml" xmlns:bib="http://bibtexml.sf.net/" xmlns:data="http://dev.w3.org/html5/spec/#custom" xmlns:epub="http://www.idpf.org/2007/ops" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:lrmi="http://lrmi.net/the-specification" class="description" itemprop="description" data-type="description">\n        By the end of this section, you will be able to: \n        <ul class="list">\n          <li class="item">Drive a car</li>\n          <li class="item">Purchase a watch</li>\n          <li class="item">Wear funny hats</li>\n          <li class="item">Eat cake</li>\n        </ul>\n      </div>\n\n      ',
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
        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        binder.append(Document('egress', io.BytesIO(u'<p>hüvasti.</p>'.encode('utf-8')),
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
        navdoc_filename = "{}.xhtml".format(binder_hash)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            [opf_filename, 'META-INF', 'contents', 'mimetype'],
            sorted(os.listdir(epub_path)))
        self.assertEqual(
            [navdoc_filename, 'egress@draft.xhtml', 'ingress@draft.xhtml'],
            sorted(os.listdir(os.path.join(epub_path, 'contents'))))

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())
        expected_nav = (
                u'<nav id="toc"><ol><li>'
                u'<a href="ingress@draft.xhtml">entrée</a>'
                u'</li><li>'
                u'<a href="egress@draft.xhtml">egress</a>'
                u'</li></ol></nav>')
        self.assertTrue(expected_nav in nav)

        # Check that translucent is set
        self.assertTrue('<span data-type="binding" data-value="translucent" />' in nav)

        # Check the title and content
        self.assertTrue('<title>Kraken</title>' in nav)
        with open(os.path.join(epub_path, 'contents', 'egress@draft.xhtml')) as f:
            egress = unescape(f.read())
        self.assertTrue('<title>egress</title>' in egress)
        self.assertTrue(u'<p>hüvasti.</p>' in egress)

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
        binder.append(Document('ingress', io.BytesIO(
            b'<p><a href="http://cnx.org/">Hello.</a></p>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        with open(os.path.join(TEST_DATA_DIR, '1x1.jpg'), 'rb') as f:
            jpg = Resource('1x1.jpg', io.BytesIO(f.read()), 'image/jpeg')
        binder.append(Document('egress', io.BytesIO(
            u'<p><img src="1x1.jpg" />hüvasti.</p>'.encode('utf-8')),
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
        navdoc_filename = "{}.xhtml".format(binder_hash)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            [opf_filename, 'META-INF', 'contents', 'mimetype', 'resources'],
            sorted(os.listdir(epub_path)))
        self.assertEqual(
            [navdoc_filename, 'egress@draft.xhtml', 'ingress@draft.xhtml'],
            sorted(os.listdir(os.path.join(epub_path, 'contents'))))
        self.assertEqual(os.listdir(os.path.join(epub_path, 'resources')),
            ['1x1.jpg'])

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())
        expected_nav = (
                u'<nav id="toc"><ol><li>'
                u'<a href="ingress@draft.xhtml">entrée</a>'
                u'</li><li>'
                u'<a href="egress@draft.xhtml">egress</a>'
                u'</li></ol></nav>')
        self.assertTrue(expected_nav in nav)

        # Check that translucent is set
        self.assertTrue('<span data-type="binding" data-value="translucent" />' in nav)

        # Check the title and content
        self.assertTrue('<title>Kraken</title>' in nav)
        with open(os.path.join(epub_path, 'contents', 'egress@draft.xhtml')) as f:
            egress = unescape(f.read())
        self.assertTrue('<title>egress</title>' in egress)
        self.assertTrue(u'<p><img src="../resources/1x1.jpg"/>hüvasti.</p>' in egress)

    def test_binder(self):
        """Create an EPUB from a binder with a few documents."""
        from ..models import Binder, Document
        binder_name = 'rock'
        binder = Binder(binder_name, metadata={'title': "Kraken"})

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
        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        binder.append(Document('egress', io.BytesIO(u'<p>hüvasti.</p>'.encode('utf-8')),
                               metadata=metadata))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_epub
        with open(epub_filepath, 'wb') as epub_file:
            make_epub(binder, epub_file)

        # Verify the results.
        epub_path = tempfile.mkdtemp('-epub')
        self.addCleanup(shutil.rmtree, epub_path)
        from ..epub import unpack_epub
        unpack_epub(epub_filepath, epub_path)

        opf_filename = "{}.opf".format(binder_name)
        navdoc_filename = "{}.xhtml".format(binder_name)

        # Check filenames, generated by id and media-type.
        self.assertEqual(
            ['META-INF', 'contents', 'mimetype', opf_filename],
            sorted(os.listdir(epub_path)))
        self.assertEqual(
            ['egress@draft.xhtml', 'ingress@draft.xhtml', navdoc_filename],
            sorted(os.listdir(os.path.join(epub_path, 'contents'))))

        # Check the nav
        with open(os.path.join(epub_path, 'contents', navdoc_filename)) as f:
            nav = unescape(f.read())
        expected_nav = (
                u'<nav id="toc"><ol><li>'
                u'<a href="ingress@draft.xhtml">entrée</a>'
                u'</li><li>'
                u'<a href="egress@draft.xhtml">egress</a>'
                u'</li></ol></nav>')
        self.assertTrue(expected_nav in nav)

        # Check that translucent is not set
        self.assertFalse('<span data-type="binding" data-value="translucent" />' in nav)

        # Check the title and content
        self.assertTrue('<title>Kraken</title>' in nav)
        with open(os.path.join(epub_path, 'contents', 'egress@draft.xhtml')) as f:
            egress = unescape(f.read())
        self.assertTrue('<title>egress</title>' in egress)
        self.assertTrue(u'<p>hüvasti.</p>' in egress)
