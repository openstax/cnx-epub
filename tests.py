# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import tempfile
import unittest

from lxml import etree


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'test-data')
SINGLE_OPF_FILEPATH = os.path.join(TEST_DATA_DIR, 'single_opf.epub')
SINGLE_OPF_METADATA = {
    # <dc:title id="title">9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6</dc:title>
    # <meta refines="#title" property="title-type">main</meta>
    'title': "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
    # <dc:creator id="creator">Connexions</dc:creator>
    # <meta refines="#creator" property="file-as">Connexions</meta>
    'creator': "Connexions",
    # <dc:identifier id="pub-id">org.cnx.contents.9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6</dc:identifier>
    'identifier': "org.cnx.contents.9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
    # <dc:language>en-US</dc:language>
    'language': "en-us",
    # <meta property="dcterms:modified">2013-06-23T12:47:00Z</meta>
    # <dc:publisher>Connexions</dc:publisher>
    'publisher': "Connexions",
    # <dc:rights>This work is shared with the public using the Attribution 3.0 Unported (CC BY 3.0) license.</dc:rights>
    'rights': "This work is shared with the public using the Attribution 3.0 Unported (CC BY 3.0) license.",
    # <link rel="cc:license" href="http://creativecommons.org/licenses/by/3.0/"/>
    'license_url': "http://creativecommons.org/licenses/by/3.0/",
    # <meta property="cc:attributionURL">http://cnx.org/content</meta>
    'base_attribution_url': "http://cnx.org/content",
    }
TEST_EPUB_FILEPATH = SINGLE_OPF_FILEPATH


class EPUBTestCase(unittest.TestCase):

    def setUp(self):
        self.cwd = tempfile.mkdtemp()
        os.chdir(self.cwd)

    def test_parsing_single_opf_success(self):
        # Parse an EPUB with a single opf entry with a few dangling items.
        from cnxepub import EPUB
        epub = EPUB.from_file(SINGLE_OPF_FILEPATH)

        # EPUBs have packages which the object treats as iterable items.
        self.assertEqual(len(epub), 1)

        package = epub[0]
        # EPUB Packages have contents... both documents and resources.
        self.assertEqual(len(package), 9)

        # Verify the package metadata.
        self.assertEqual(package.metadata, SINGLE_OPF_METADATA)

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
        from cnxepub import EPUB

        epub1 = EPUB.from_file(SINGLE_OPF_FILEPATH)
        epub2 = EPUB.from_file(SINGLE_OPF_FILEPATH)

        self.assertEqual(len(epub1), 1)
        self.assertEqual(len(epub1[0]), 9)
        self.assertEqual(len(epub2), 1)
        self.assertEqual(len(epub2[0]), 9)


class HtmlMetadataParsingTestCase(unittest.TestCase):

    def test_uid_ordering(self):
        from cnxepub import _parse_document_metadata as parser

        filepath = os.path.join(TEST_DATA_DIR, 'ordered-uids.xhtml')
        with open(filepath, 'r') as fb:
            doc = etree.parse(fb)
        metadata = parser(doc)

        expected =  ['Author 3', 'Author 12', 'Author 4',
                     'Author 1', 'Author 10']
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

class EPubParsingTestCase(unittest.TestCase):
    # This only checks the adaptation, not the archival the content.
    #   Minimal database interaction is required

    def test_epub(self):
        # Parses a collection oriented epub content to file mappings.
        from cnxepub import EPUB
        epub = EPUB.from_file(TEST_EPUB_FILEPATH)

        # Chop the epub apart.
        from cnxepub import epub_to_mapping
        mapping = epub_to_mapping(epub)

        expected_package_mapping = {
            # '{filename}': [{document-data-key}, ...],
            'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml': ['document', 'type',
                                                             'metadata'],
            '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml': ['tree', 'type',
                                                               'metadata'],
            '3c448dc6-d5f5-43d5-8df7-fe27d462bd3a@1.xhtml': ['document', 'type',
                                                             'metadata'],
            'ad17c39c-d606-4441-b987-54448020bb40@2.xhtml': ['document', 'type',
                                                             'metadata'],
            '7c52af05-05b1-4761-aa4c-b17b0197dc6d@1.xhtml': ['document', 'type',
                                                             'metadata'],
            }

        dense_mapping = {k:v.keys() for k, v in mapping[0].items()}
        self.assertEqual(dense_mapping, expected_package_mapping)

    @unittest.skip("not implemented, waiting to see if the base cases "
                   "(formatting and values) are acceptable.")
    def test_collection_w_extras(self):
        # Parse an epub containing content that is not referenced within the
        #   navigation or documents.
        from cnxepub import EPUB
        epub = EPUB.from_file(TEST_EPUB_W_EXTRAS_FILEPATH)

        # Check that it dropped the extra content.
