# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import io
import json
import sys
import unittest
try:
    from unittest import mock
except ImportError:
    import mock


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'data')

IS_PY3 = sys.version_info.major == 3


class BaseModelTestCase(unittest.TestCase):

    def make_binder(self, id=None, nodes=None, metadata=None):
        """Make a ``Binder`` instance.
        If ``id`` is not supplied, a ``TranslucentBinder`` is made.
        """
        from ..models import Binder, TranslucentBinder
        if id is None:
            binder = TranslucentBinder(nodes, metadata)
        else:
            binder = Binder(id, nodes, metadata)
        return binder

    def make_document(self, id, content=b'', metadata={}):
        from ..models import Document
        return Document(id, io.BytesIO(content), metadata=metadata)

    def make_document_pointer(self, ident_hash, metadata={}):
        from ..models import DocumentPointer
        return DocumentPointer(ident_hash, metadata=metadata)

    def make_resource(self, *args, **kwargs):
        from ..models import Resource
        return Resource(*args, **kwargs)


class ModelAttributesTestCase(BaseModelTestCase):

    def test_binder_attribs(self):
        binder = self.make_binder('8d75ea29@3')

        self.assertEqual(binder.id, '8d75ea29')
        self.assertEqual(binder.ident_hash, '8d75ea29@3')
        self.assertEqual(binder.metadata['version'], '3')

        binder.ident_hash = '67e4ag@4.5'
        self.assertEqual(binder.id, '67e4ag')
        self.assertEqual(binder.ident_hash, '67e4ag@4.5')
        self.assertEqual(binder.metadata['version'], '4.5')

        with self.assertRaises(ValueError) as caughtexception:
            binder.ident_hash = '67e4ag'
            self.assertContains(caughtexception, 'requires version')

        del binder.id
        with self.assertRaises(AttributeError) as caughtexception:
            _ = binder.id
            self.assertContains(caughtexception, 'object has no attribute')

        binder.id = '456@2'
        self.assertEqual(binder.id, '456')
        self.assertEqual(binder.ident_hash, '456@2')
        self.assertEqual(binder.metadata['version'], '2')

    def test_document_attribs(self):
        document = self.make_document('8d75ea29@3')

        self.assertEqual(document.id, '8d75ea29')
        self.assertEqual(document.ident_hash, '8d75ea29@3')
        self.assertEqual(document.metadata['version'], '3')

        document.ident_hash = '67e4ag@4.5'
        self.assertEqual(document.id, '67e4ag')
        self.assertEqual(document.ident_hash, '67e4ag@4.5')
        self.assertEqual(document.metadata['version'], '4.5')

        with self.assertRaises(ValueError) as caughtexception:
            document.ident_hash = '67e4ag'
            self.assertContains(caughtexception, 'requires version')

        del document.id
        with self.assertRaises(AttributeError) as caughtexception:
            _ = document.id
            self.assertContains(caughtexception, 'object has no attribute')

        document.id = '456@2'
        self.assertEqual(document.id, '456')
        self.assertEqual(document.ident_hash, '456@2')
        self.assertEqual(document.metadata['version'], '2')


class TreeUtilityTestCase(BaseModelTestCase):

    def test_binder_to_tree(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_binder(
                    None,
                    metadata={'title': "Part One"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter One"},
                            nodes=[
                                self.make_document(
                                    id="e78d4f90",
                                    metadata={'version': '3',
                                              'title': "Document One"})]),
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Two"},
                            nodes=[
                                self.make_document(
                                    id="3c448dc6",
                                    metadata={'version': '1',
                                              'title': "Document Two"})])]),
                self.make_binder(
                    None,
                    metadata={'title': "Part Two"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Three"},
                            nodes=[
                                self.make_document(
                                    id="ad17c39c",
                                    metadata={'version': '2',
                                              'title': "Document Three"})])]),
                self.make_binder(
                    '4e5390a5@2',
                    metadata={'title': "Part Three"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Four"},
                            nodes=[
                                self.make_document(
                                    id="7c52af05",
                                    metadata={'version': '1',
                                              'title': "Document Four"})])])])

        expected_tree = {
            'id': '8d75ea29@3',
            'shortId': None,
            'contents': [
                {'id': 'subcol',
                 'shortId': None,
                 'contents': [
                     {'id': 'subcol',
                      'shortId': None,
                      'contents': [
                          {'id': 'e78d4f90@3',
                           'shortId': None,
                           'title': 'Document One'}],
                      'title': 'Chapter One'},
                     {'id': 'subcol',
                      'shortId': None,
                      'contents': [
                          {'id': '3c448dc6@1',
                           'shortId': None,
                           'title': 'Document Two'}],
                      'title': 'Chapter Two'}],
                 'title': 'Part One'},
                {'id': 'subcol',
                 'shortId': None,
                 'contents': [
                     {'id': 'subcol',
                      'shortId': None,
                      'contents': [
                          {'id': 'ad17c39c@2',
                           'shortId': None,
                           'title': 'Document Three'}],
                      'title': 'Chapter Three'}],
                 'title': 'Part Two'},
                {'id': '4e5390a5@2',
                 'shortId': None,
                 'contents': [
                     {'id': 'subcol',
                      'shortId': None,
                      'contents': [
                          {'id': '7c52af05@1',
                           'shortId': None,
                           'title': 'Document Four'}],
                      'title': 'Chapter Four'}],
                 'title': 'Part Three'}],
            'title': 'Book One'}

        from ..models import model_to_tree
        tree = model_to_tree(binder)
        self.assertEqual(tree, expected_tree)

    def test_flatten_model(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_binder(
                    None,
                    metadata={'title': "Part One"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter One"},
                            nodes=[
                                self.make_document(
                                    id="e78d4f90",
                                    metadata={'version': '3',
                                              'title': "Document One"})]),
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Two"},
                            nodes=[
                                self.make_document(
                                    id="3c448dc6",
                                    metadata={'version': '1',
                                              'title': "Document Two"})])]),
                self.make_binder(
                    None,
                    metadata={'title': "Part Two"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Three"},
                            nodes=[
                                self.make_document(
                                    id="ad17c39c",
                                    metadata={'version': '2',
                                              'title': "Document Three"})])])])
        expected_titles = [
            'Book One',
            'Part One',
            'Chapter One', 'Document One',
            'Chapter Two', 'Document Two',
            'Part Two',
            'Chapter Three', 'Document Three']

        from ..models import flatten_model
        titles = [m.metadata['title'] for m in flatten_model(binder)]
        self.assertEqual(titles, expected_titles)

    def test_flatten_to_documents(self):
        binder = self.make_binder(
            '8d75ea29',
            metadata={'version': '3', 'title': "Book One"},
            nodes=[
                self.make_binder(
                    None,
                    metadata={'title': "Part One"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter One"},
                            nodes=[
                                self.make_document(
                                    id="e78d4f90",
                                    metadata={'version': '3',
                                              'title': "Document One"})]),
                        self.make_document_pointer(
                            ident_hash='844a99e5@1',
                            metadata={'title': "Pointing"}),
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Two"},
                            nodes=[
                                self.make_document(
                                    id="3c448dc6",
                                    metadata={'version': '1',
                                              'title': "Document Two"})])]),
                self.make_binder(
                    None,
                    metadata={'title': "Part Two"},
                    nodes=[
                        self.make_binder(
                            None,
                            metadata={'title': "Chapter Three"},
                            nodes=[
                                self.make_document(
                                    id="ad17c39c",
                                    metadata={'version': '2',
                                              'title': "Document Three"})])])])

        from ..models import flatten_to_documents

        # Test for default, Document only results.
        expected_titles = ['Document One', 'Document Two', 'Document Three']
        titles = [d.metadata['title'] for d in flatten_to_documents(binder)]
        self.assertEqual(titles, expected_titles)

        # Test for included DocumentPointer results.
        expected_titles = ['Document One', 'Pointing', 'Document Two',
                           'Document Three']
        titles = [d.metadata['title']
                  for d in flatten_to_documents(binder, include_pointers=True)]
        self.assertEqual(titles, expected_titles)


class ModelBehaviorTestCase(unittest.TestCase):

    def test_document_w_references(self):
        """Documents are loaded then parsed to show their
        references within the HTML content.
        """
        expected_uris = ["http://example.com/people/old-mcdonald",
                         "http://cnx.org/contents/5f3acd92@3",
                         "../resources/nyan-cat.gif"
                         ]
        content = """\
<body>
<h1> McDonald Bio </h1>
<p>There is a farmer named <a href="{}">Old McDonald</a>. Plants grow on his farm and animals live there. He himself is vegan, and so he wrote a book about <a href="{}">Vegan Farming</a>.</p>
<img src="{}"/>
<span>Ei ei O.</span>
</body>
""".format(*expected_uris)

        from ..models import Document
        document = Document('mcdonald', content)

        self.assertEqual(len(document.references), 3)
        are_external = [r.remote_type == 'external'
                        for r in document.references]
        self.assertEqual([True, True, False], are_external)
        self.assertEqual(expected_uris, [r.uri for r in document.references])

        # reload the content
        document.content = content
        # update some references
        document.references[0].uri = 'https://example.com/people/old-mcdonald'
        self.assertTrue(b'<a href="https://example.com/people/old-mcdonald">'
                        in document.content)

    def test_document_w_bound_references(self):
        starting_uris = ["../resources/openstax.png",
                         "m23409.xhtml",
                         ]
        content = """\
<body>
<h1>Reference replacement test-case</h1>
<p>Link to <a href="{}">a local legacy module</a>.</p>
<img src="{}"/>
<p>Fin.</p>
</body>
""".format(*starting_uris)

        from ..models import Document
        document = Document('document', content)

        self.assertEqual(len(document.references), 2)
        are_external = [r.remote_type == 'external'
                        for r in document.references]
        self.assertEqual([False, False], are_external)
        self.assertEqual(starting_uris, [r.uri for r in document.references])

        # Now bind the model to the reference.
        resource_uri_tmplt = "/resources/{}"
        resource_name = '36ad78c3'
        resource = mock.Mock()
        resource.id = resource_name
        document.references[0].bind(resource, "/resources/{}")

        expected_uris = [
            resource_uri_tmplt.format(resource_name),
            starting_uris[1],
            ]
        self.assertEqual(expected_uris, [r.uri for r in document.references])

        # And change it the resource identifier
        changed_resource_name = 'smoo.png'
        resource.id = changed_resource_name
        expected_uris = [
            resource_uri_tmplt.format(changed_resource_name),
            starting_uris[1],
            ]
        self.assertEqual(expected_uris, [r.uri for r in document.references])

    def test_document_content(self):
        with open(
            os.path.join(TEST_DATA_DIR,
                         'fb74dc89-47d4-4e46-aac1-b8682f487bd5@1.json'),
                'r') as f:
            metadata = json.loads(f.read())
        from ..models import Document
        document = Document('document', metadata['content'])
        self.assertTrue(b'To demonstrate the potential of online publishing'
                        in document.content)
