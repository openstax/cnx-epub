# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import unittest
try:
    from unittest import mock
except ImportError:
    import mock


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')


class AdaptationTestCase(unittest.TestCase):

    def make_package(self, file):
        from ..epub import Package
        return Package.from_file(file)

    def make_item(self, file, **kwargs):
        from ..epub import Item
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

        from ..adapters import adapt_package
        binder = adapt_package(package)

        # This checks the binder structure, and only taps at the documents.
        from ..models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)

    def test_to_translucent_binder(self):
        """Adapts a ``Package`` to a ``TranslucentBinder``.
        Translucent binders are native object representations of data,
        while the Package is merely a representation of EPUB structure.
        Furthermore, translucent binders are non-persistable objects,
        that contain the same behavior as binders, but lack metadata
        and material. They can be thought of as a protective sheath that
        is invisible, yet holds the contents together.
        """
        # Easiest way to test this is using the ``model_to_tree`` utility
        # to analyze the structural equality.
        package_filepath = os.path.join(
            TEST_DATA_DIR, 'loose-pages', "faux.opf")
        package = self.make_package(package_filepath)
        expected_tree = {
            'id': 'subcol',
            'title': "Loose Pages",
            'contents': [{'id': None, 'title': 'Yummy'},
                         {'id': None, 'title': 'Da bomb'}],
            }

        from ..adapters import adapt_package
        binder = adapt_package(package)

        # This checks the binder structure, and only taps at the documents.
        from ..models import model_to_tree
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
        from ..adapters import adapt_item
        document = adapt_item(item, package)

        self.fail('incomplete')
        # Check the document metadata
        pass
        # Check the document uri lookup
        pass
        # Check resource discovery.
        pass
