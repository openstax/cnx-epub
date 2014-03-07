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
import zipfile
from unittest import mock

from lxml import etree


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'test-data')


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def pack_epub(self, directory):
        """Given an directory containing epub contents,
        pack it up and make return filepath.
        Packed file is remove on test exit.
        """
        zip_fd, zip_filepath = tempfile.mkstemp('.epub', dir=self.tmpdir)
        with zipfile.ZipFile(zip_filepath, 'w') as zippy:
            base_path = os.path.abspath(directory)
            for root, dirs, filenames in os.walk(directory):
                # Strip the absolute path
                archive_path = os.path.abspath(root)[len(base_path):]
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    archival_filepath = os.path.join(archive_path, filename)
                    zippy.write(filepath, archival_filepath)
        return zip_filepath

    def copy(self, src, dst_name='book'):
        """Convenient method for copying test data directories."""
        dst = os.path.join(self.tmpdir, dst_name)
        shutil.copytree(src, dst)
        return dst


class EPUBTestCase(BaseTestCase):

    def test_obj_from_unknown_file_type(self):
        """Test that we get an exception when
        an unknown filetype is given.
        """
        # For example purposes, use any file within the test-data directory.
        filepath = os.path.join(TEST_DATA_DIR, 'nav-tree.xhtml')

        from . import EPUB
        with self.assertRaises(TypeError) as caught_exception:
            epub = EPUB.from_file(filepath)

    def test_obj_from_directory(self):
        """Test that we can read an (unarchived) epub from the filesystem."""
        epub_filepath = os.path.join(TEST_DATA_DIR, 'blank')

        from . import EPUB
        epub = EPUB.from_file(epub_filepath)

        self.assertEqual(epub._root, epub_filepath)

    def test_obj_from_epub_file(self):
        """Test that we can read an .epub file."""
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'blank'))

        from . import EPUB
        epub = EPUB.from_file(epub_filepath)

        # Does it unpack to a temporary location?
        self.assertTrue(epub._root.startswith(tempfile.tempdir))

    def test_obj_from_open_epub_file(self):
        """Test that we can read an open .epub file."""
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'blank'))

        from .import EPUB
        with open(epub_filepath, 'rb') as zf:
            epub = EPUB.from_file(zf)

        # Does it unpack to a temporary location?
        self.assertTrue(epub._root.startswith(tempfile.tempdir))
        from .epub import (
            EPUB_MIMETYPE_RELATIVE_PATH,
            EPUB_MIMETYPE_CONTENTS,
            )
        mimetype_filepath = os.path.join(epub._root,
                                         EPUB_MIMETYPE_RELATIVE_PATH)
        with open(mimetype_filepath, 'r') as fb:
            contents = fb.read().strip()
            self.assertEqual(contents, EPUB_MIMETYPE_CONTENTS)

    def test_package_parsing(self):
        """Test that packages are parsed into the EPUB.
        This does not examine whether the packages themselves are correct,
        only that the packages are represented within the EPUB object.
        """
        # Use the book test data, which contains a single package with
        # valid values all the way down.
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'book'))

        # Parse an EPUB.
        from cnxepub import EPUB
        epub = EPUB.from_file(epub_filepath)

        # EPUBs have packages which the object treats as iterable items.
        self.assertEqual(len(epub), 1)


class PackageTestCase(BaseTestCase):

    def make_one(self, file):
        from .epub import Package
        return Package.from_file(file)

    def test_wo_navigation_item(self):
        """Navigation documents are required in a valid EPUB.
        We will enforce this requirement, as we (cnx) also need the navigation
        document in order to build a tree of publishable items.
        """
        # Copy the test data to modify it.
        epub_filepath = os.path.join(TEST_DATA_DIR, 'book')
        epub_root = os.path.join(self.tmpdir, 'book')
        shutil.copytree(epub_filepath, epub_root)
        package_filepath = os.path.join(
            epub_root,
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        # Remove the navigation item from the 'book' test data.
        with open(package_filepath, 'r') as fb:
            xml = etree.parse(fb)
        from .epub import EPUB_OPF_NAMESPACES as opf_nsmap
        manifest = xml.xpath('//opf:manifest', namespaces=opf_nsmap)[0]
        nav_item = xml.xpath('//opf:item[@properties="nav"]',
                             namespaces=opf_nsmap)[0]
        del manifest[manifest.index(nav_item)]
        with open(package_filepath, 'wb') as fb:
            fb.write(etree.tostring(xml))

        from .epub import MissingNavigationError as Error
        with self.assertRaises(Error) as caught_exception:
            package = self.make_one(package_filepath)

    def test_w_double_navigation_item(self):
        """Navigation documents are required in a valid EPUB.
        We will enfource this requirement, as we (cnx) also need the navigation
        document in order to build a tree of publishable items.
        However, we need to limit the navigation to one per package,
        because in our scheme the package's navigation document defines
        a book tree.
        """
        # Copy the test data to modify it.
        epub_root = self.copy(os.path.join(TEST_DATA_DIR, 'book'))
        package_filepath = os.path.join(
            epub_root,
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        # Remove the navigation item from the 'book' test data.
        with open(package_filepath, 'r') as fb:
            xml = etree.parse(fb)
        from .epub import EPUB_OPF_NAMESPACES as opf_nsmap
        manifest = xml.xpath('//opf:manifest', namespaces=opf_nsmap)[0]
        nav_item = xml.xpath('//opf:item[@properties="nav"]',
                             namespaces=opf_nsmap)[0]
        from copy import deepcopy
        nav_item = deepcopy(nav_item)
        nav_item.set('id', "toc2")
        manifest.append(nav_item)
        with open(package_filepath, 'wb') as fb:
            fb.write(etree.tostring(xml))

        from .epub import AdditionalNavigationError as Error
        with self.assertRaises(Error) as caught_exception:
            package = self.make_one(package_filepath)

    def test_metadata_parsing(self):
        """With a completely NEW package
        (NOT based on or derived from any other work),
        check parsed metadata for accuracy.
        """
        package_filepath = os.path.join(
            TEST_DATA_DIR, 'book',
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        package = self.make_one(package_filepath)

        expected_metadata = {
            'publisher': "Connexions",
            'publication_message': "Loosely publishing these here modules.",
            'identifier': "org.cnx.contents.9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'title': "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'language': "en-us",
            'publisher': "Connexions",
            'license_text': "This work is shared with the public using the Attribution 3.0 Unported (CC BY 3.0) license.",
            'license_url': "http://creativecommons.org/licenses/by/3.0/",
            }
        self.assertEqual(package.metadata, expected_metadata)

    def test_item_containment(self):
        package_filepath = os.path.join(
            TEST_DATA_DIR, 'book',
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        package = self.make_one(package_filepath)
        # EPUB Packages have contents...
        self.assertEqual(len(package), 3)

        # Check the navigation order
        expected_nav_document = package.grab_by_name(
                "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml")
        self.assertTrue(expected_nav_document.is_navigation)
        self.assertEqual(package.navigation, expected_nav_document)

        # Verify reference to a resource item.
        # This also checks iteration and containment
        resource = [i for i in package
                    if i.name == "e3d625fe893b3f1f9aaef3bdf6bfa15c.png"][0]
        self.assertIn(resource, package)

    def test_parsing_same_file_twice(self):
        # Tests identity issues accross more than one instance.
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'book'))

        from cnxepub import EPUB
        epub1 = EPUB.from_file(epub_filepath)
        epub2 = EPUB.from_file(epub_filepath)

        self.assertEqual(len(epub1), 1)
        self.assertEqual(len(epub1[0]), 3)
        self.assertEqual(len(epub2), 1)
        self.assertEqual(len(epub2[0]), 3)


class TreeUtilityTestCase(unittest.TestCase):

    def make_binder(self, id=None, nodes=None, metadata=None):
        """Make a ``Binder`` instance.
        If ``id`` is not supplied, a ``FauxBinder`` is made.
        """
        from .models import Binder, TranslucentBinder
        if id is None:
            binder = TranslucentBinder(nodes, metadata)
        else:
            binder = Binder(id, nodes, metadata)
        return binder

    def make_document(self, id, metadata={}):
        from .models import Document
        return Document(id, io.StringIO(''), metadata=metadata)

    maxDiff = None
    def test_binder_to_tree(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_binder(
                    None,
                    metadata={'title': "Part One"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter One"},
                            nodes=[
                                self.make_document(
                                    id="e78d4f90",
                                    metadata={'version': '3',
                                              'title': "Document One"})]),
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Two"},
                            nodes=[
                                self.make_document(
                                    id="3c448dc6",
                                    metadata={'version': '1',
                                              'title': "Document Two"})])]),
                self.make_binder(
                    None,
                    metadata={'title': "Part Two"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Three"},
                            nodes=[
                                self.make_document(
                                    id="ad17c39c",
                                    metadata={'version': '2',
                                              'title': "Document Three"})])]),
                self.make_binder(
                    None,
                    metadata={'title': "Part Three"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Four"},
                            nodes=[
                                self.make_document(
                                    id="7c52af05",
                                    metadata={'version': '1',
                                              'title': "Document Four"})])])])

        expected_tree = {
            'id': '8d75ea29@3',
            'contents': [
                {'id': 'subcol',
                 'contents': [
                     {'id': 'subcol',
                      'contents': [
                          {'id': 'e78d4f90@3',
                           'title': 'Document One'}],
                      'title': 'Chapter One'},
                     {'id': 'subcol',
                      'contents': [
                          {'id': '3c448dc6@1',
                           'title': 'Document Two'}],
                      'title': 'Chapter Two'}],
                 'title': 'Part One'},
                {'id': 'subcol',
                 'contents': [
                    {'id': 'subcol',
                     'contents': [
                         {'id': 'ad17c39c@2',
                          'title': 'Document Three'}],
                     'title': 'Chapter Three'}],
                 'title': 'Part Two'},
                {'id': 'subcol',
                 'contents': [
                     {'id': 'subcol',
                      'contents': [
                          {'id': '7c52af05@1',
                           'title': 'Document Four'}],
                      'title': 'Chapter Four'}],
                 'title': 'Part Three'}],
            'title': 'Book One'}

        from .models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)


class HTMLParsingTestCase(unittest.TestCase):

    def test_metadata_parsing(self):
        """Verify the parsing of metadata from an HTML document."""
        html_doc_filepath = os.path.join(
            TEST_DATA_DIR, 'book', 'content',
            'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml')
        from .html_parsers import parse_metadata
        with open(html_doc_filepath, 'r') as fb:
            html = etree.parse(fb)
            metadata = parse_metadata(html)
        expected_metadata = {
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
            'copyright_holders': [],
            'created': '2013/03/19 15:01:16 -0500',
            'editors': [],
            'illustrators': [],
            'keywords': ['South Africa'],
            'license_text': 'CC-By 4.0',
            'license_url': 'http://creativecommons.org/licenses/by/4.0/',
            'publishers': [],
            'revised': '2013/06/18 15:22:55 -0500',
            'subjects': ['Science and Mathematics'],
            'title': 'Document One of Infinity',
            'translators': [],
            }
        self.assertEqual(metadata, expected_metadata)

    def test_resource_parsing(self):
        """Look for resources within the document"""
        self.fail('incomplete')

class AdaptationTestCase(unittest.TestCase):

    def make_package(self, file):
        from . import Package
        return Package.from_file(file)

    def make_item(self, file, **kwargs):
        from . import Item
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

        from .adapters import adapt_package
        binder = adapt_package(package)

        # This checks the binder structure, and only taps at the documents.
        from .models import model_to_tree
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
        item = self.make_item(item_filepath)

        package = mock.Mock()
        # This would not typically be called outside the context of
        # a package, but in the case of a scoped test we use it.
        from .adapters import adapt_item
        document = adapt_item(item, package)

        self.fail('incomplete')
        # Check the document metadata
        pass
        # Check the document uri lookup
        pass
        # Check resource discovery.
        pass
