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
