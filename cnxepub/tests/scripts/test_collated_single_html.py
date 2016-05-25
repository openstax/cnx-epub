# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import io
import mimetypes
import os.path
import sys
import tempfile
import unittest

from lxml import etree

from ...html_parsers import HTML_DOCUMENT_NAMESPACES
from ...testing import TEST_DATA_DIR, captured_output

IS_PY3 = sys.version_info.major == 3


class CollatedSingleHTMLTestCase(unittest.TestCase):
    maxDiff = None

    @property
    def target(self):
        from ...scripts.collated_single_html.main import main
        return main

    @property
    def path_to_xhtml(self):
        return os.path.join(TEST_DATA_DIR, 'desserts-single-page.xhtml')

    def test_valid(self):
        return_code = self.target([self.path_to_xhtml])
        self.assertEqual(return_code, 0)

    def test_valid_with_tree(self):
        # Capture stdout
        orig_stdout = sys.stdout
        self.addCleanup(setattr, sys, 'stdout', orig_stdout)
        if IS_PY3:
            stdout = sys.stdout = io.TextIOWrapper(io.BytesIO())
        else:
            stdout = sys.stdout = io.BytesIO()

        return_code = self.target([self.path_to_xhtml, '-d'])
        self.assertEqual(return_code, 0)

        stdout.seek(0)
        self.assertIn("'title': 'Fruity'", stdout.read())
