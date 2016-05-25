# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import mimetypes
import os.path
import tempfile
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from ...html_parsers import HTML_DOCUMENT_NAMESPACES
from ...testing import TEST_DATA_DIR, captured_output


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
