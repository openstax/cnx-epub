# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import io
import hashlib
import mimetypes
try:
    from collections.abc import MutableSequence, Iterable
except ImportError:
    from collections import MutableSequence, Iterable
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from contextlib import contextmanager

import lxml.html
import lxml.html.builder
from lxml import etree


__all__ = (
    'TRANSLUCENT_BINDER_ID', 'RESOURCE_HASH_TYPE',
    'INTERNAL_REFERENCE_TYPE', 'EXTERNAL_REFERENCE_TYPE',
    'REFERENCE_REMOTE_TYPES',
    'ATTRIBUTED_ROLE_KEYS',
    'flatten_tree_to_ident_hashes', 'model_to_tree',
    'flatten_model', 'flatten_to_documents',
    'Binder', 'TranslucentBinder', 'Document', 'DocumentPointer', 'Resource',
    )


mimetypes.init()
RESOURCE_HASH_TYPE = 'sha1'
TRANSLUCENT_BINDER_ID = 'subcol'
INTERNAL_REFERENCE_TYPE = 'internal'
EXTERNAL_REFERENCE_TYPE = 'external'
INLINE_REFERENCE_TYPE = 'inline'
REFERENCE_REMOTE_TYPES = (INTERNAL_REFERENCE_TYPE, EXTERNAL_REFERENCE_TYPE, INLINE_REFERENCE_TYPE,)
ATTRIBUTED_ROLE_KEYS = (
    # MUST be alphabetical
    'authors', 'copyright_holders', 'editors', 'illustrators',
    'publishers', 'translators',
    )


def utf8(item):
    if isinstance(item, list):
        return [utf8(i) for i in item]
    if isinstance(item, dict):
        return {utf8(k): utf8(v) for k, v in item.items()}
    try:
        return item.decode('utf-8')
    except:
        return item


def model_to_tree(model, title=None, lucent_id=TRANSLUCENT_BINDER_ID):
    """Given an model, build the tree::

        {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}

    """
    if type(model) is TranslucentBinder:
        id = lucent_id
    else:
        id = model.ident_hash
    title = title is not None and title or model.metadata.get('title')
    tree = {'id': id, 'title': title}
    if hasattr(model, '__iter__'):
        contents = tree['contents'] = []
        for node in model:
            item = model_to_tree(node, model.get_title_for_node(node),
                                 lucent_id=lucent_id)
            contents.append(item)
    return tree


def flatten_tree_to_ident_hashes(item_or_tree, lucent_id=TRANSLUCENT_BINDER_ID):
    """Flatten a tree to id and version values (ident_hash)."""
    if 'contents' in item_or_tree:
        tree = item_or_tree
        if tree['id'] != lucent_id:
            yield tree['id']
        for i in tree['contents']:
            ##yield from flatten_tree_to_ident_hashs(i, lucent_id)
            for x in flatten_tree_to_ident_hashes(i, lucent_id):
                yield x
    else:
        item = item_or_tree
        yield item['id']
    raise StopIteration()


def flatten_model(model):
    """Flatten a model to a list of models.
    This is used to flatten a ``Binder``'ish model down to a list
    of contained models.
    """
    yield model
    if isinstance(model, (TranslucentBinder, Binder,)):
        for m in model:
            ##yield from flatten_model(m)
            for x in flatten_model(m):
                yield x
    raise StopIteration()


def flatten_to_documents(model, include_pointers=False):
    """Flatten the model to a list of documents (aka ``Document`` objects).
    This is to flatten a ``Binder``'ish model down to a list of documents.
    If ``include_pointers`` has been set to ``True``, ``DocumentPointers``
    will also be included in the results.
    """
    for m in flatten_model(model):
        if isinstance(m, Document):
            yield m
        elif include_pointers and isinstance(m, DocumentPointer):
            yield m
    raise StopIteration()


def _discover_uri_type(uri):
    """Given a ``uri``, determine if it is internal or external."""
    parsed_uri = urlparse(uri)
    if not parsed_uri.netloc:
        if parsed_uri.scheme == 'data':
            type_ = INLINE_REFERENCE_TYPE
        else:
            type_ = INTERNAL_REFERENCE_TYPE
    else:
        type_ = EXTERNAL_REFERENCE_TYPE
    return type_

def _parse_references(xml):
    """Parse the references to ``Reference`` instances."""
    references = []
    ref_finder = HTMLReferenceFinder(xml)
    for elm, uri_attr in ref_finder:
        type_ = _discover_uri_type(elm.get(uri_attr))
        references.append(Reference(elm, type_, uri_attr))
    return references


class Reference(object):
    """A reference within a ``Document`` model, either internal or external.
    This depends on an xml element tree, to provide binds for uri and name.
    """

    def __init__(self, elm, remote_type, uri_attr):
        self.elm = elm
        try:
            assert remote_type in REFERENCE_REMOTE_TYPES
        except AssertionError:
            raise ValueError("remote_type: '{}' is invalid." \
                             .format(remote_type))
        self.remote_type = remote_type
        self._uri_attr = uri_attr
        self._bound_model = None
        self._uri_template = None

    @property
    def is_bound(self):
        return self._bound_model is not None

    # read-only property, use bind for writing.
    @property
    def bound_model(self):
        return self._bound_model

    def _get_uri(self):
        if self.is_bound:
            # Update the value before returning.
            self._set_uri_from_bound_model()
        return self.elm.get(self._uri_attr)

    def _set_uri(self, value):
        if self.is_bound:
            raise ValueError("URI is bound to an object. Unbind first.")
        self.elm.set(self._uri_attr, value)

    uri = property(_get_uri, _set_uri)

    @property
    def uri_parts(self):
        """Returns a parsed URI"""
        return urlparse(self.uri)

    def _set_uri_from_bound_model(self):
        """Using the bound model, set the uri."""
        value = self._uri_template.format(self._bound_model.id)
        self.elm.set(self._uri_attr, value)

    def bind(self, model, template="{}"):
        """Bind the ``model`` to the reference. This uses the model's
        ``id`` attribute and the given ``template`` to
        dynamically produce a uri when accessed.
        """
        self._bound_model = model
        self._uri_template = template
        self._set_uri_from_bound_model()

    def unbind(self):
        """Unbind the model from the reference."""
        self._bound_model = None
        self._uri_template = None


class HTMLReferenceFinder(object):
    """Find references within an HTML xml element tree."""

    def __init__(self, xml):
        self.xml = xml

    def __iter__(self):
        for elm in self._archors():
            yield elm, 'href'
        for elm, uri_attr in self._media():
            yield elm, uri_attr
        raise StopIteration()

    def apply_xpath(self, xpath):
        return self.xml.xpath(xpath)

    def _archors(self):
        return self.apply_xpath('//a')

    def _media(self):
        media_xpath = {
                '//img[@src]': 'src',
                '//audio[@src]': 'src',
                '//video[@src]': 'src',
                '//object[@data]': 'data',
                '//object/embed[@src]': 'src',
                '//source[@src]': 'src',
                '//span[@data-src]': 'data-src',
                }
        for xpath, attr in media_xpath.items():
            for elm in self.apply_xpath(xpath):
                yield elm, attr
        raise StopIteration()


# ########## #
#   Models   #
# ########## #

class TranslucentBinder(MutableSequence):
    """A clear/translucent binder instance.
    This is used only represent ``Binder`` behavior
    without being a persistent piece of data.
    """
    id = None
    ident_hash = None

    def __init__(self, nodes=None, metadata=None,
                 title_overrides=None):
        self._nodes = nodes or []
        self.metadata = utf8(metadata or {})
        if title_overrides is not None:
            if len(self._nodes) != len(title_overrides):
                raise ValueError(
                    "``title_overrides`` should be the same length as "
                    "``nodes``. {} != {}" \
                    .format(len(self._nodes), len(title_overrides)))
            self._title_overrides = utf8(title_overrides)
        else:
            self._title_overrides = [None] * len(self._nodes)

    @property
    def ident_hash(self):
        return None

    @property
    def is_translucent(self):
        return self.__class__ is TranslucentBinder

    def set_title_for_node(self, node, title):
        index = self._nodes.index(node)
        self._title_overrides[index] = title

    def get_title_for_node(self, node):
        index = self._nodes.index(node)
        return self._title_overrides[index]

    # ABC methods for MutableSequence
    def __getitem__(self, i):
        return self._nodes[i]

    def __setitem__(self, i, v):
        self._nodes[i] = v

    def __delitem__(self, i):
        del self._nodes[i]
        del self._title_overrides[i]

    def __len__(self):
        return len(self._nodes)

    def insert(self, i, v):
        self._nodes.insert(i, v)
        self._title_overrides.insert(i, None)


class Binder(TranslucentBinder):
    """An object that has metadata and contains
    ``Binder``, ``TranslucentBinder`` and ``Document`` instances.
    """

    def __init__(self, id, nodes=None, metadata=None, title_overrides=None):
        super(Binder, self).__init__(nodes, metadata, title_overrides)
        self.id = id

    @property
    def ident_hash(self):
        if self.id is not None:
            args = [self.id]
            version = self.metadata.get('version')
            if version is not None:
                args.append(version)
            value = '@'.join(args)
        else:
            value = None
        return value

    def get_uri(self, system, default=None):
        try:
            uri = self.metadata["{}-uri".format(system)]
        except KeyError:
            return default
        return uri

    def set_uri(self, system, value):
        key = "{}-uri".format(system)
        self.metadata[key] = value


class Document(object):
    """An HTML document noted as ``content`` on the instance,
    which can contain ``Resource`` instances.
    """
    media_type = 'application/xhtml+xml'

    def __init__(self, id, data, metadata=None, resources=None,
                 reference_resolver=None):
        self.id = id
        self._xml = None
        if hasattr(data, 'read'):
            self.content = utf8(data.read())
        else:
            self.content = utf8(data)
        self._references = _parse_references(self._xml)
        self.metadata = utf8(metadata or {})
        self.resources = resources or []

    @property
    def html(self):
        html = lxml.html.builder.HTML(
            lxml.html.fragment_fromstring(self.content, 'body'))
        return utf8(lxml.html.tostring(html, method='xml'))

    def _content__get(self):
        """Produce the content from the data.
        This is used to write out reference changes that may have
        taken place.
        """
        string_types = (type(u''), type(b''))
        # Unwrap the xml.
        content = [isinstance(node, string_types) and node or etree.tostring(node)
                   for node in self._xml.xpath('node()')]
        return ''.join(utf8(content))

    def _content__set(self, value):
        self._xml = lxml.html.fragment_fromstring(value, 'div')
        # reload the references after a content update
        self._references = _parse_references(self._xml)

    def _content__del(self):
        self._xml = etree.Element('div')

    content = property(_content__get,
                       _content__set,
                       _content__del,
                       _content__get.__doc__)

    @property
    def ident_hash(self):
        if self.id is not None:
            args = [self.id]
            version = self.metadata.get('version')
            if version is not None:
                args.append(version)
            value = '@'.join(args)
        else:
            value = None
        return value

    def get_uri(self, system, default=None):
        try:
            uri = self.metadata["{}-uri".format(system)]
        except KeyError:
            return default
        return uri

    def set_uri(self, system, value):
        key = "{}-uri".format(system)
        self.metadata[key] = value

    @property
    def references(self):
        """Reference points in the document.
        These could be resources, other documents, external links, etc.
        """
        if self._references is None:
            return []
        return self._references


class DocumentPointer(object):
    media_type = 'application/xhtml+xml'

    def __init__(self, ident_hash, metadata=None):
        self.ident_hash = ident_hash
        self.id = ident_hash
        self.metadata = metadata is not None and metadata or {}

    @classmethod
    def from_uri(cls, uri):
        parts = urlparse(uri)
        split_path = parts.path.split('/')
        ident_hash = split_path[-1]
        return cls(ident_hash)


class Resource(object):
    """A binary object used within the context of the ``Document``.
    It is typically referenced within the documents HTML content.
    """

    def __init__(self, id, data, media_type, filename=None):
        self.id = id
        if not isinstance(data, io.BytesIO):
            raise ValueError("Data must be an io.BytesIO instance. "
                             "'{}' was given.".format(type(data)))
        self._data = data
        self.media_type = media_type

        self._hash = hashlib.new(RESOURCE_HASH_TYPE,
                                 self._data.read()).hexdigest()
        if not filename:
            # Create a filename from the hash and media-type.
            filename = "{}.{}".format(
                self._hash, mimetypes.guess_extension(self.media_type))
        self.filename = filename

        self._data.seek(0)

    @property
    def hash(self):
        return self._hash

    @contextmanager
    def open(self):
        self._data.seek(0)
        yield self._data
        self._data.seek(0)
