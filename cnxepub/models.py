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
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from contextlib import contextmanager

from lxml import etree


__all__ = (
    'TRANSLUCENT_BINDER_ID', 'RESOURCE_HASH_TYPE',
    'INTERNAL_REFERENCE_TYPE', 'EXTERNAL_REFERENCE_TYPE',
    'REFERENCE_REMOTE_TYPES',
    'ATTRIBUTED_ROLE_KEYS',
    'flatten_tree_to_ident_hashes', 'model_to_tree',
    'flatten_model', 'flatten_to', 'flatten_to_documents',
    'Binder', 'TranslucentBinder',
    'Document', 'CompositeDocument', 'DocumentPointer',
    'Resource',
    'content_to_etree', 'etree_to_content',
    )


mimetypes.init()
RESOURCE_HASH_TYPE = 'sha1'
TRANSLUCENT_BINDER_ID = 'subcol'
INTERNAL_REFERENCE_TYPE = 'internal'
EXTERNAL_REFERENCE_TYPE = 'external'
INLINE_REFERENCE_TYPE = 'inline'
REFERENCE_REMOTE_TYPES = (
    INTERNAL_REFERENCE_TYPE, EXTERNAL_REFERENCE_TYPE, INLINE_REFERENCE_TYPE,)
ATTRIBUTED_ROLE_KEYS = (
    # MUST be alphabetical
    'authors', 'copyright_holders', 'editors', 'illustrators',
    'publishers', 'translators',
    )
XML_WRAPPER = u"""\
<div
  xmlns="http://www.w3.org/1999/xhtml"
  xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
  xmlns:epub="http://www.idpf.org/2007/ops"
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:lrmi="http://lrmi.net/the-specification"
  xmlns:math="http://www.w3.org/1998/Math/MathML"
  xmlns:qml="http://cnx.rice.edu/qml/1.0"
  xmlns:datadev="http://dev.w3.org/html5/spec/#custom"
  xmlns:modids="http://cnx.rice.edu/#moduleIds"
  xmlns:bib="http://bibtexml.sf.net/"
  xmlns:md="http://cnx.rice.edu/mdml"
  xmlns:cnxml="http://cnx.rice.edu/cnxml"
  >
{}
</div>"""

XHTML_NS = {'x': 'http://www.w3.org/1999/xhtml'}


def utf8(item):
    if isinstance(item, list):
        return [utf8(i) for i in item]
    if isinstance(item, dict):
        return {utf8(k): utf8(v) for k, v in item.items()}
    try:
        return item.decode('utf-8')
    except (UnicodeEncodeError, AttributeError):
        # py2 and py3 errs, respectively, for when fed an encoded string
        return item


def content_to_etree(content):
    if not content:  # Allow building empty models
        return etree.XML('<div xmlns="http://www.w3.org/1999/xhtml" />')
    xml_parser = etree.XMLParser(ns_clean=True)
    tree = etree.XML(content, xml_parser)
    # Determine if we've been fed a full XHTML page, with a <body> tag:
    bods = tree.xpath('//*[self::body|self::x:body]',
                      namespaces={'x': 'http://www.w3.org/1999/xhtml'})
    if bods:
        bods[0].tag = '{http://www.w3.org/1999/xhtml}div'
        return bods[0]
    else:  # It parsed, so must have been fed a valid XML tree - return it
        return tree


def etree_to_content(etree_):
    return etree.tostring(etree_)


def model_to_tree(model, title=None, lucent_id=TRANSLUCENT_BINDER_ID):
    """Given an model, build the tree::

        {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}

    """
    id = model.ident_hash
    if id is None and isinstance(model, TranslucentBinder):
        id = lucent_id
    md = model.metadata
    shortid = md.get('shortId', md.get('cnx-archive-shortid'))
    title = title is not None and title or md.get('title')
    tree = {'id': id, 'title': title, 'shortId': shortid}
    if hasattr(model, '__iter__'):
        contents = tree['contents'] = []
        for node in model:
            item = model_to_tree(node, model.get_title_for_node(node),
                                 lucent_id=lucent_id)
            contents.append(item)
    return tree


def flatten_tree_to_ident_hashes(item_or_tree,
                                 lucent_id=TRANSLUCENT_BINDER_ID):
    """Flatten a tree to id and version values (ident_hash)."""
    if 'contents' in item_or_tree:
        tree = item_or_tree
        if tree['id'] != lucent_id:
            yield tree['id']
        for i in tree['contents']:
            # yield from flatten_tree_to_ident_hashs(i, lucent_id)
            for x in flatten_tree_to_ident_hashes(i, lucent_id):
                yield x
    else:
        item = item_or_tree
        yield item['id']


def flatten_model(model):
    """Flatten a model to a list of models.
    This is used to flatten a ``Binder``'ish model down to a list
    of contained models.
    """
    yield model
    if isinstance(model, (TranslucentBinder, Binder,)):
        for m in model:
            # yield from flatten_model(m)
            for x in flatten_model(m):
                yield x


def flatten_to_documents(model, include_pointers=False):
    """Flatten the model to a list of documents (aka ``Document`` objects).
    This is to flatten a ``Binder``'ish model down to a list of documents.
    If ``include_pointers`` has been set to ``True``, ``DocumentPointers``
    will also be included in the results.

    """
    types = [Document]
    if include_pointers:
        types.append(DocumentPointer)
    types = tuple(types)

    def _filter(m):
        return isinstance(m, types)

    return flatten_to(model, _filter)


def flatten_to(model, flatten_filter):
    """Flatten the model to a list of models that meet criteria of
    the given `flatten_filter` callable.

    `flatten_filter` should take one argument, the model that
    is being iterated over, and return a boolean to indicate that
    the model meets the criteria for inclusion in the returned list.

    """
    for m in flatten_model(model):
        if flatten_filter(m):
            yield m


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
            raise ValueError("remote_type: '{}' is invalid."
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
        for elm in self._anchors():
            yield elm, 'href'
        for elm, uri_attr in self._media():
            yield elm, uri_attr

    def apply_xpath(self, xpath, namespaces=None):
        return self.xml.xpath(xpath, namespaces=namespaces)

    def _anchors(self):
        return self.apply_xpath('//*[self::a[@href]|self::x:a[@href]]',
                                XHTML_NS)

    def _media(self):
        media_xpath = [
                ['//img[@src]', 'src', None],
                ['//audio[@src]', 'src', None],
                ['//video[@src]', 'src', None],
                ['//object[@data]', 'data', None],
                ['//object/embed[@src]', 'src', None],
                ['//source[@src]', 'src', None],
                ['//span[@data-src]', 'data-src', None],
                ['//x:img[@src]', 'src', XHTML_NS],
                ['//x:audio[@src]', 'src', XHTML_NS],
                ['//x:video[@src]', 'src', XHTML_NS],
                ['//x:object[@data]', 'data', XHTML_NS],
                ['//x:object/embed[@src]', 'src', XHTML_NS],
                ['//x:source[@src]', 'src', XHTML_NS],
                ['//x:span[@data-src]', 'data-src', XHTML_NS],
                ]
        for xpath, attr, ns in media_xpath:
            for elm in self.apply_xpath(xpath, ns):
                yield elm, attr


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
                    "``nodes``. {} != {}"
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
    ``Binder``, ``Resource``, ``TranslucentBinder`` and ``Document`` instances.
    """

    def __init__(self, id, nodes=None, metadata=None, title_overrides=None,
                 resources=None):
        super(Binder, self).__init__(nodes, metadata, title_overrides)
        self.id = id
        self.resources = resources or []

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):

        if value and '@' in value:
            self._id, self.metadata['version'] = value.split('@')
        else:
            self._id = value

    @id.deleter
    def id(self):
        del self._id

    @property
    def ident_hash(self):
        if self.id not in (None, TRANSLUCENT_BINDER_ID):
            args = [self.id]
            version = self.metadata.get('version')
            if version is not None:
                args.append(version)
            value = '@'.join(args)
        else:
            value = None
        return value

    @ident_hash.setter
    def ident_hash(self, value):

        try:
            self._id, self.metadata['version'] = value.split('@')
        except ValueError:
            raise ValueError("ident_hash requires a version", value)

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
        self._xml = None
        if hasattr(data, 'read'):
            self.content = utf8(data.read())
        else:
            self.content = utf8(data)
        self._references = _parse_references(self._xml)
        self.metadata = utf8(metadata or {})
        self.resources = resources or []
        self.id = id

    def _content__get(self):
        """Produce the content from the data.
        This is used to write out reference changes that may have
        taken place.
        """
        return etree_to_content(self._xml)

    def _content__set(self, value):
        self._xml = content_to_etree(value)
        # reload the references after a content update
        self._references = _parse_references(self._xml)

    def _content__del(self):
        self._xml = etree.Element('div')

    content = property(_content__get,
                       _content__set,
                       _content__del,
                       _content__get.__doc__)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):

        if value and '@' in value:
            self._id, self.metadata['version'] = value.split('@')
        else:
            self._id = value

    @id.deleter
    def id(self):
        del self._id

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

    @ident_hash.setter
    def ident_hash(self, value):

        try:
            self._id, self.metadata['version'] = value.split('@')
        except ValueError:
            raise ValueError("ident_hash requires a version", value)

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
        self.metadata = utf8(metadata or {})

    @classmethod
    def from_uri(cls, uri):
        parts = urlparse(uri)
        split_path = parts.path.split('/')
        ident_hash = split_path[-1]
        return cls(ident_hash)


class CompositeDocument(Document):
    """A Document created during the collation process."""


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
            filename = "{}{}".format(
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
