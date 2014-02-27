# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import tempfile
import shutil
import unittest
import zipfile

from lxml import etree


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'test-data')


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp_dir)

    def pack_epub(self, directory):
        """Given an directory containing epub contents,
        pack it up and make return filepath.
        Packed file is remove on test exit.
        """
        zip_fd, zip_filepath = tempfile.mkstemp('.epub', dir=self.tmp_dir)
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



class EPUBTestCase(BaseTestCase):

    def test_parsing_success(self):
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'book'))

        # Parse an EPUB.
        from cnxepub import EPUB
        epub = EPUB.from_filepath(epub_filepath)

        # EPUBs have packages which the object treats as iterable items.
        self.assertEqual(len(epub), 1)

        package = epub[0]
        # EPUB Packages have contents... both documents and resources.
        self.assertEqual(len(package), 3)

        # Verify the package metadata.
        # The important bits to check for are our custom properties
        expected_package_metadata = {
            'title': "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'creator': "Connexions",
            'identifier': "org.cnx.contents.9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'language': "en-us",
            'publisher': "Connexions",
            'rights': "This work is shared with the public using the Attribution 3.0 Unported (CC BY 3.0) license.",
            'license_url': "http://creativecommons.org/licenses/by/3.0/",
            'base_attribution_url': "http://cnx.org/contents",
            'publication_message': "Loosely publishing these here modules.",
        }
        self.assertEqual(package.metadata, expected_package_metadata)

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

    def test_two_navigation_items_fails(self):
        # Expect failure when two navigation items exist.

        # Copy the test 'book' and modify it to include
        #   a second navigation document.
        epub_dir = os.path.join(self.tmp_dir, 'book')
        shutil.copytree(os.path.join(TEST_DATA_DIR, 'book'), epub_dir)
        package_filepath = os.path.join(
                epub_dir, '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf')
        package_doc = etree.parse(package_filepath)
        from cnxepub import EPUB_OPF_NAMESPACES
        manifest = package_doc.xpath('//opf:manifest',
                                     namespaces=EPUB_OPF_NAMESPACES)[0]
        from copy import deepcopy
        manifest.append(deepcopy(manifest[0]))
        with open(package_filepath, 'w') as fb:
            fb.write(str(etree.tostring(package_doc), encoding='utf-8'))

        epub_filepath = self.pack_epub(epub_dir)
        # We only fail on navigation item retrieval. This may not be complete?
        from cnxepub import EPUB
        epub = EPUB.from_file(epub_filepath)

        with self.assertRaises(ValueError) as caught_assertion:
            navigation = epub[0].navigation
        exception = caught_assertion.exception
        self.assertTrue(exception.args[0].lower().find('only one') >= 0)

    def test_zero_navigation_items_fails(self):
        # Expect failure when zero navigation items exist.

        # Copy the test 'book' and modify it to include
        #   a second navigation document.
        epub_dir = os.path.join(self.tmp_dir, 'book')
        shutil.copytree(os.path.join(TEST_DATA_DIR, 'book'), epub_dir)
        package_filepath = os.path.join(
                epub_dir, '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf')
        package_doc = etree.parse(package_filepath)
        from cnxepub import EPUB_OPF_NAMESPACES
        manifest = package_doc.xpath('//opf:manifest',
                                     namespaces=EPUB_OPF_NAMESPACES)[0]
        from copy import deepcopy
        del manifest[0]
        with open(package_filepath, 'w') as fb:
            fb.write(str(etree.tostring(package_doc), encoding='utf-8'))

        epub_filepath = self.pack_epub(epub_dir)
        # We only fail on navigation item retrieval. This may not be complete?
        from cnxepub import EPUB
        epub = EPUB.from_file(epub_filepath)

        with self.assertRaises(ValueError) as caught_assertion:
            navigation = epub[0].navigation
        exception = caught_assertion.exception
        self.assertTrue(exception.args[0].lower().find('not found') >= 0)


class EPubParsingTestCase(BaseTestCase):
    maxDiff = None

    def test_epub(self):
        # Parses a collection oriented epub content to file mappings.
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'book'))

        from cnxepub import EPUB
        epub = EPUB.from_file(epub_filepath)

        # Chop the epub apart.
        from cnxepub import epub_to_mapping
        mapping = epub_to_mapping(epub)

        expected_package_mapping = {
            # '{filename}': [{document-data-key}, ...],
            'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml': ['document',
                                                             'metadata', 'type'],
            '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml': ['metadata',
                                                               'tree', 'type'],
            }

        dense_mapping = {k:sorted(v.keys()) for k, v in mapping[0].items()}
        self.assertEqual(dense_mapping, expected_package_mapping)

    @unittest.skip("not implemented, waiting to see if the base cases "
                   "(formatting and values) are acceptable.")
    def test_collection_w_extras(self):
        # Parse an epub containing content that is not referenced within the
        #   navigation or documents.
        from cnxepub import EPUB
        epub = EPUB.from_file(TEST_EPUB_W_EXTRAS_FILEPATH)

        # Check that it dropped the extra content.


class AdaptationTestCase(unittest.TestCase):

    def test_package_to_collection(self):
        # Adapt a package to a collection.
        # A collection in this context is an object that has
        #   metadata and contains subcollections and/or modules.
        # A subcollection in this context is an object that does
        #   not contain the full set of metadata,
        #   but does have a human readable title.
        # A module is then an object that like collections contains metadata
        #   and optionally contains resources.
        # Resources are any auxiliary file referenced within the module(s).
        pass

class HtmlMetadataParsingTestCase(unittest.TestCase):

    def test_uid_ordering(self):
        from cnxepub import _parse_document_metadata as parser

        filepath = os.path.join(TEST_DATA_DIR, 'book', 'content',
                                'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml')
        with open(filepath, 'r') as fb:
            doc = etree.parse(fb)
        metadata = parser(doc)

        expected =  ['Mark Horner', 'Sarah Blyth', 'Charmaine St. Rose']
        self.assertEqual(metadata['authors'], expected)


class HtmlNavigationParsingTestCase(unittest.TestCase):

    def test_parsing(self):
        from cnxepub import Item, _parse_epub_navigation

        filepath = os.path.join(TEST_DATA_DIR, 'nav-tree.xhtml')
        with open(filepath) as fb:
            item = Item('no-name', fb)
            docs, tree, metadata = _parse_epub_navigation(item)

        expected_docs = ['e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml',
                         '3c448dc6-d5f5-43d5-8df7-fe27d462bd3a@1.xhtml',
                         'ad17c39c-d606-4441-b987-54448020bb40@2.xhtml',
                         '7c52af05-05b1-4761-aa4c-b17b0197dc6d@1.xhtml',
                         ]
        expected_tree = {
            'id': 'no-name',
            'contents': [
                {'id': 'subcol',
                 'contents': [
                     {'id': 'subcol',
                      'contents': [
                          {'id': 'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml',
                           'title': 'Document One'}],
                      'title': 'Chapter One'},
                     {'id': 'subcol',
                      'contents': [
                          {'id': '3c448dc6-d5f5-43d5-8df7-fe27d462bd3a@1.xhtml',
                           'title': 'Document Two'}],
                      'title': 'Chapter Two'}],
                 'title': 'Part One'},
                {'id': 'subcol',
                 'contents': [
                    {'id': 'subcol',
                     'contents': [
                         {'id': 'ad17c39c-d606-4441-b987-54448020bb40@2.xhtml',
                          'title': 'Document Three'}],
                     'title': 'Chapter Three'}],
                 'title': 'Part Two'},
                {'id': 'subcol',
                 'contents': [
                     {'id': 'subcol',
                      'contents': [
                          {'id': '7c52af05-05b1-4761-aa4c-b17b0197dc6d@1.xhtml',
                           'title': 'Document Four'}],
                      'title': 'Chapter Four'}],
                 'title': 'Part Three'}],
            'title': 'Book One'}

        self.assertEqual(docs, expected_docs)
        self.assertEqual(tree, expected_tree)
