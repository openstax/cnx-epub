# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import mimetypes
import os.path
import sys
import tempfile
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from lxml import etree

from ...html_parsers import HTML_DOCUMENT_NAMESPACES
from ...testing import TEST_DATA_DIR, captured_output


IS_PY3 = sys.version_info.major == 3


def mocked_guess_extension(*args, **kwargs):
    # Fix what extension is returned by mimetypes.guess_extension
    # for the test
    exts = mimetypes.guess_all_extensions(*args, **kwargs)
    return sorted(exts)[-1]


@mock.patch('mimetypes.guess_extension', mocked_guess_extension)
class SingleHTMLTestCase(unittest.TestCase):
    @property
    def target(self):
        from ...scripts.single_html.main import main
        return main

    epub_path = os.path.join(TEST_DATA_DIR, 'book')

    maxDiff = None

    def xpath(self, path):
        return self.root.xpath(path, namespaces=HTML_DOCUMENT_NAMESPACES)

    def test_w_mathjax(self):
        with captured_output() as (out, err):
            self.target(['-m', 'latest', self.epub_path])
        stdout = out.getvalue()
        stderr = err.getvalue()

        self.assertEqual(stderr, '')

        self.root = etree.fromstring(stdout)
        self.assertEqual(
            ['https://cdn.mathjax.org/mathjax/latest/unpacked/MathJax.js?'
             'config=MML_HTMLorMML'],
            self.xpath('xhtml:head/xhtml:script/@src'))

        with captured_output() as (out, err):
            self.target(['-m', '2.4', self.epub_path])
        stdout = out.getvalue()
        stderr = err.getvalue()

        self.assertEqual(stderr, '')

        self.root = etree.fromstring(stdout)
        self.assertEqual(
            ['https://cdn.mathjax.org/mathjax/2.4-latest/unpacked/MathJax.js?'
             'config=MML_HTMLorMML'],
            self.xpath('xhtml:head/xhtml:script/@src'))

    def test_w_html_out(self):
        import random
        random.seed(1)

        html_path = os.path.join(
            TEST_DATA_DIR, 'book-single-page-actual.xhtml')
        if not IS_PY3:
            html_path = html_path.replace(
                '.xhtml', '-py2.xhtml')

        with captured_output() as (out, err):
            self.target([self.epub_path, html_path])
        stdout = out.getvalue()
        stderr = err.getvalue()
        self.assertEqual(stdout, '')
        self.assertEqual(stderr, '')

        expected_html_path = os.path.join(
            TEST_DATA_DIR, 'book-single-page.xhtml')
        if not IS_PY3:
            expected_html_path = expected_html_path.replace(
                '.xhtml', '-py2.xhtml')
        with open(expected_html_path, 'r') as expected:
            with open(html_path, 'r') as actual:
                self.assertMultiLineEqual(expected.read(), actual.read())
        os.remove(html_path)

    def test_blank_epub(self):
        with self.assertRaises(Exception) as cm:
            self.target([os.path.join(TEST_DATA_DIR, 'blank')])

        self.assertEqual(str(cm.exception), 'Expecting an epub with one book')

    def test_w_verbose(self):
        from ...scripts.single_html.main import logger

        # Remove logger stderr handler so it doesn't print debug statements
        logger.removeHandler(logger.handlers[0])

        with captured_output() as (out, err):
            self.target(['-v', self.epub_path])
        stderr = err.getvalue()

        self.assertTrue(stderr.startswith('Full binder:'))

    def test_w_subset_chapters_1(self):
        with captured_output() as (out, err):
            self.target(['-s', '1', self.epub_path])
        stdout = out.getvalue()
        stderr = err.getvalue()
        self.assertEqual(stderr, '')

        self.root = etree.fromstring(stdout)
        self.assertEqual(1, len(self.xpath('xhtml:body/*[@data-type="unit"]')))
        self.assertEqual(1, len(self.xpath('//*[@data-type="chapter"]')))

    def test_w_subset_chapters_2(self):
        with captured_output() as (out, err):
            self.target(['-s', '2', self.epub_path])
        stdout = out.getvalue()

        self.root = etree.fromstring(stdout)
        self.assertEqual(1, len(self.xpath('xhtml:body/*[@data-type="unit"]')))
        self.assertEqual(2, len(self.xpath('//*[@data-type="chapter"]')))

    def test_w_subset_chapters_3(self):
        with captured_output() as (out, err):
            self.target(['-s', '3', self.epub_path])
        stdout = out.getvalue()

        self.root = etree.fromstring(stdout)
        self.assertEqual(2, len(self.xpath('xhtml:body/*[@data-type="unit"]')))
        self.assertEqual(3, len(self.xpath('//*[@data-type="chapter"]')))

    def test_w_subset_chapters_4(self):
        with captured_output() as (out, err):
            self.target(['-s', '4', self.epub_path])
        stdout = out.getvalue()

        self.root = etree.fromstring(stdout)
        self.assertEqual(2, len(self.xpath('xhtml:body/*[@data-type="unit"]')))
        self.assertEqual(3, len(self.xpath('//*[@data-type="chapter"]')))
