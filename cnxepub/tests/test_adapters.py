# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
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
        with open(item_filepath, 'w') as fb:
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
        metadata.update({'title': "ingress"})
        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        binder.append(Document('egress', io.BytesIO(b'<p>Goodbye.</p>'),
                               metadata=metadata))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_publication_epub
        with open(epub_filepath, 'w') as epub_file:
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
            nav = f.read()
        expected_nav = (
                '<nav id="toc"><ol><li>'
                '<a href="/contents/ingress@draft.xhtml">ingress</a>'
                '</li><li>'
                '<a href="/contents/egress@draft.xhtml">egress</a>'
                '</li></ol></nav>')
        self.assertTrue(expected_nav in nav)

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
        metadata.update({'title': "ingress"})
        binder.append(Document('ingress', io.BytesIO(b'<p>Hello.</p>'),
                               metadata=metadata))
        metadata = base_metadata.copy()
        metadata.update({'title': "egress"})
        binder.append(Document('egress', io.BytesIO(b'<p>Goodbye.</p>'),
                               metadata=metadata))

        # Call the target.
        fs_pointer, epub_filepath = tempfile.mkstemp('.epub')
        self.addCleanup(os.remove, epub_filepath)
        from ..adapters import make_epub
        with open(epub_filepath, 'w') as epub_file:
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
            nav = f.read()
        expected_nav = (
                '<nav id="toc"><ol><li>'
                '<a href="/contents/ingress@draft.xhtml">ingress</a>'
                '</li><li>'
                '<a href="/contents/egress@draft.xhtml">egress</a>'
                '</li></ol></nav>')
        self.assertTrue(expected_nav in nav)
