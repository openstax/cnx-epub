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
        expected_nav_document = package.grab_by_name("9b0903d2-13c4-4ebe-9ffe-1ee79db28482@1.6.xhtml")
        self.assertTrue(expected_nav_document.is_navigation)
        self.assertEqual(package.navigation_doc, expected_nav_document)

        # Verify reference to a resource item.
        # This also checks iteration and containment
        resource = [i for i in package
                    if i.name == "e3d625fe893b3f1f9aaef3bdf6bfa15c.png"][0]
        self.assertIn(resource, package)
