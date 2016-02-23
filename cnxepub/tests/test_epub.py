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

from .. import testing


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


class EPUBTestCase(testing.EPUBTestCase):

    @property
    def target_cls(self):
        """Import the target class"""
        from ..epub import EPUB
        return EPUB

    def test_obj_from_unknown_file_type(self):
        """Test that we get an exception when
        an unknown filetype is given.
        """
        # For example purposes, use any file within the test-data directory.
        filepath = os.path.join(TEST_DATA_DIR, 'nav-tree.xhtml')

        with self.assertRaises(TypeError) as caught_exception:
            epub = self.target_cls.from_file(filepath)

    def test_obj_from_directory(self):
        """Test that we can read an (unarchived) epub from the filesystem."""
        epub_filepath = os.path.join(TEST_DATA_DIR, 'blank')

        epub = self.target_cls.from_file(epub_filepath)

        self.assertEqual(epub._root, epub_filepath)

    def test_obj_from_epub_file(self):
        """Test that we can read an .epub file."""
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'blank'))

        epub = self.target_cls.from_file(epub_filepath)

        # Does it unpack to a temporary location?
        self.assertTrue(epub._root.startswith(tempfile.tempdir))

    def test_obj_from_open_epub_file(self):
        """Test that we can read an open .epub file."""
        epub_filepath = self.pack_epub(os.path.join(TEST_DATA_DIR, 'blank'))

        with open(epub_filepath, 'rb') as zf:
            epub = self.target_cls.from_file(zf)

        # Does it unpack to a temporary location?
        self.assertTrue(epub._root.startswith(tempfile.tempdir))
        from ..epub import (
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
        epub = self.target_cls.from_file(epub_filepath)

        # EPUBs have packages which the object treats as iterable items.
        self.assertEqual(len(epub), 1)


class PackageTestCase(testing.EPUBTestCase):

    def make_one(self, file):
        from ..epub import Package
        return Package.from_file(file)

    def test_wo_navigation_item(self):
        """Navigation documents are required in a valid EPUB.
        We will enforce this requirement, as we (cnx) also need the navigation
        document in order to build a tree of publishable items.
        """
        # Copy the test data to modify it.
        epub_filepath = os.path.join(TEST_DATA_DIR, 'book')
        epub_root = self.copy(epub_filepath)
        package_filepath = os.path.join(
            epub_root,
            "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf")
        # Remove the navigation item from the 'book' test data.
        with open(package_filepath, 'r') as fb:
            xml = etree.parse(fb)
        from ..epub import EPUB_OPF_NAMESPACES as opf_nsmap
        manifest = xml.xpath('//opf:manifest', namespaces=opf_nsmap)[0]
        nav_item = xml.xpath('//opf:item[@properties="nav"]',
                             namespaces=opf_nsmap)[0]
        del manifest[manifest.index(nav_item)]
        with open(package_filepath, 'wb') as fb:
            fb.write(etree.tostring(xml))

        from ..epub import MissingNavigationError as Error
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
        from ..epub import EPUB_OPF_NAMESPACES as opf_nsmap
        manifest = xml.xpath('//opf:manifest', namespaces=opf_nsmap)[0]
        nav_item = xml.xpath('//opf:item[@properties="nav"]',
                             namespaces=opf_nsmap)[0]
        from copy import deepcopy
        nav_item = deepcopy(nav_item)
        nav_item.set('id', "toc2")
        manifest.append(nav_item)
        with open(package_filepath, 'wb') as fb:
            fb.write(etree.tostring(xml))

        from ..epub import AdditionalNavigationError as Error
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
            'publication_message': u'Nueva Versión',
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
        self.assertEqual(len(package), 4)

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

        from ..epub import EPUB
        epub1 = EPUB.from_file(epub_filepath)
        epub2 = EPUB.from_file(epub_filepath)

        self.assertEqual(len(epub1), 1)
        self.assertEqual(len(epub1[0]), 4)
        self.assertEqual(len(epub2), 1)
        self.assertEqual(len(epub2[0]), 4)


class WritePackageTestCase(testing.EPUBTestCase):
    """Output the ``Package`` to the filesystem"""

    def test_to_file(self):
        """Write a populated Package to the filesystem."""
        # Use the 'book' data to test against. This enables us to
        # test the resulting structure against the existing structure.

        # Packages are not mutable and shouldn't be, because one wouldn't
        # normally create a package by hand. It would be created via
        # the reading from the filesystem or through adaptation of
        # a ``Binder``'ish object.
        book_path = os.path.join(TEST_DATA_DIR, 'book')
        from ..epub import Item
        items = [
            {'filepath': os.path.join(
                book_path, 'content',
                '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml'),
             'media_type': 'application/xhtml+xml',
             'is_navigation': True,
             'properties': ['nav'],
             },
            {'filepath': os.path.join(
                 book_path, 'content',
                 'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml'),
             'media_type': 'application/xhtml+xml',
             },
            {'filepath': os.path.join(
                 book_path, 'resources',
                 'e3d625fe893b3f1f9aaef3bdf6bfa15c.png'),
             'media_type': 'image/png',
             }
            ]
        items = [Item.from_file(**i) for i in items]

        package_name = '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf'
        package_metadata = {
            'publisher': "Connexions",
            'publication_message': "Loosely publishing these here modules.",
            'title': "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'identifier': "org.cnx.contents.9b0903d2-13c4-4ebe-"
                          "9ffe-1ee79db28482@1.6",
            'language': 'en-us',
            'license_text': "This work is shared with the public using "
                            "the Attribution 3.0 Unported (CC BY 3.0) "
                            "license.",
            'license_url': "http://creativecommons.org/licenses/by/3.0/",
            }
        from ..epub import Package
        package = Package(package_name, items, package_metadata)

        output_path = self.tmpdir
        package.to_file(package, output_path)

        # Verify...
        walker = os.walk(output_path)
        for root, dirs, files in walker:
            break
        self.assertEqual(['contents', 'resources'], sorted(dirs))
        self.assertEqual([package_name], files)
        # ./contents/
        files = os.listdir(os.path.join(output_path, 'contents'))
        self.assertEqual(['9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml',
                          'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml'],
                         sorted(files))
        # ./resources/
        files = os.listdir(os.path.join(output_path, 'resources'))
        self.assertEqual(['e3d625fe893b3f1f9aaef3bdf6bfa15c.png'],
                         sorted(files))

        with open(os.path.join(output_path, package_name), 'r') as fb:
            opf_xml = etree.parse(fb)

        # Parse the file and see if the metadata matches.
        from ..epub import OPFParser
        parser = OPFParser(opf_xml)

        self.assertEqual(parser.metadata, package_metadata)


class WriteEPUBTestCase(testing.EPUBTestCase):
    """Output the ``EPUB`` to the filesystem"""

    def test_to_file(self):
        """Write a populated EPUB to the filesystem as a zipfile."""
        # Use the 'book' data to test against. This enables us to
        # test the resulting structure against the existing structure.

        # EPUB and Package are not mutable and shouldn't be,
        # because one wouldn't normally create an EPUB by hand.
        # It would be created via the reading from the filesystem
        # or through adaptation of a ``Binder``'ish object(s).
        book_path = os.path.join(TEST_DATA_DIR, 'book')
        from ..epub import Item
        items = [
            {'filepath': os.path.join(
                book_path, 'content',
                '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml'),
             'media_type': 'application/xhtml+xml',
             'is_navigation': True,
             'properties': ['nav'],
             },
            {'filepath': os.path.join(
                 book_path, 'content',
                 'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml'),
             'media_type': 'application/xhtml+xml',
             },
            {'filepath': os.path.join(
                 book_path, 'resources',
                 'e3d625fe893b3f1f9aaef3bdf6bfa15c.png'),
             'media_type': 'image/png',
             }
            ]
        items = [Item.from_file(**i) for i in items]

        package_name = '9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.opf'
        package_metadata = {
            'publisher': "Connexions",
            'publication_message': "Loosely publishing these here modules.",
            'title': "9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6",
            'identifier': "org.cnx.contents.9b0903d2-13c4-4ebe-"
                          "9ffe-1ee79db28482@1.6",
            'language': 'en-us',
            'license_text': "This work is shared with the public using "
                            "the Attribution 3.0 Unported (CC BY 3.0) "
                            "license.",
            'license_url': "http://creativecommons.org/licenses/by/3.0/",
            }
        from ..epub import Package
        package = Package(package_name, items, package_metadata)

        from ..epub import EPUB
        epub = EPUB(packages=[package])

        output_path = self.tmpdir
        epub_filename = 'book.epub'
        epub_filepath = os.path.join(output_path, epub_filename)
        epub.to_file(epub, epub_filepath)

        # Unpack so we can check the contents...
        from ..epub import unpack_epub
        unpack_path = os.path.join(self.tmpdir, 'unpacked-epub')
        os.mkdir(unpack_path)
        epub_directory = unpack_epub(epub_filepath, unpack_path)

        # Verify...
        walker = os.walk(unpack_path)
        for root, dirs, files in walker:
            break
        self.assertEqual(['META-INF', 'contents', 'resources'],
                         sorted(dirs))
        self.assertEqual([package_name, 'mimetype'], sorted(files))
        # ./META-INF/
        files = os.listdir(os.path.join(unpack_path, 'META-INF'))
        self.assertEqual(['container.xml'], files)
        # ./contents/
        files = os.listdir(os.path.join(unpack_path, 'contents'))
        self.assertEqual(['9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml',
                          'e78d4f90-e078-49d2-beac-e95e8be70667@3.xhtml'],
                         sorted(files))
        # ./resources/
        files = os.listdir(os.path.join(unpack_path, 'resources'))
        self.assertEqual(['e3d625fe893b3f1f9aaef3bdf6bfa15c.png'], files)

        from ..epub import EPUB_CONTAINER_XML_RELATIVE_PATH
        container_xml_filepath = os.path.join(unpack_path,
                                              EPUB_CONTAINER_XML_RELATIVE_PATH)
        with open(container_xml_filepath, 'r') as fb:
            container_xml = fb.read()

        with open(os.path.join(unpack_path, 'mimetype'), 'r') as fb:
            self.assertEqual(fb.read(), 'application/epub+zip')

        # Parse the file and check for opf inclusion.
        expected_string = 'full-path="{}"'.format(package_name)
        self.assertTrue(container_xml.find(expected_string) >= 0,
                        container_xml)
