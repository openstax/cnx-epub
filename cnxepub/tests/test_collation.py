# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest

from .test_models import BaseModelTestCase


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


@unittest.skip("not implemented")
class XXXEasyBakeTestCase(unittest.TestCase):

    def test(self):
        import io
        _input = """
<html><body>
<div data-type="book">
  <div data-type="page">
    <span>content</span>
  </div>
</div>
</body></html>"""
        input = io.BytesIO(_input)
        output = io.BytesIO()

        # Ensure same in, same out
        from cnxepub.collation import easybake
        easybake('ruleset', input, output)
        output.seek(0)

        self.assertIn(output.read(), "<span> pseudo cooked </span>")


@unittest.skip("not implemented")
class ReconstituteTestCase(unittest.TestCase):

    def test(self):
        self.fail("not implemented")


class CollateTestCase(BaseModelTestCase):

    @property
    def target(self):
        from cnxepub import collate
        return collate

    @unittest.skip("work in progress")
    def test(self):
        self.fail("work in progress")

    def test_without_ruleset(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_document(
                    id="e78d4f90",
                    metadata={'version': '3',
                              'title': "Document One"}),
                self.make_document(
                    id="3c448dc6",
                    metadata={'version': '1',
                              'title': "Document Two"})])

        result = self.target(binder)
        self.assertIs(binder, result)
