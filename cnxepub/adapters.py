# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import base64
import io
import logging
import mimetypes
import os
import uuid

from copy import deepcopy

import jinja2
import lxml.html

from lxml import etree

from .epub import EPUB, Package, Item
from .formatters import HTMLFormatter
from .models import (
    flatten_model, flatten_to_documents,
    content_to_etree, etree_to_content,
    Binder, TranslucentBinder,
    Document, Resource, DocumentPointer, CompositeDocument,
    TRANSLUCENT_BINDER_ID,
    INTERNAL_REFERENCE_TYPE,
    INLINE_REFERENCE_TYPE,
    )
from .html_parsers import (parse_metadata, parse_navigation_html_to_tree,
                           parse_resources, DocumentPointerMetadataParser,
                           HTML_DOCUMENT_NAMESPACES)

from .data_uri import DataURI


logger = logging.getLogger('cnxepub')


__all__ = (
    'adapt_package', 'adapt_item',
    'get_model_extensions',
    'make_epub', 'make_publication_epub',
    'BinderItem',
    'DocumentItem',
    'adapt_single_html',
    )


class AdaptationError(Exception):
    """Raised when data is not able to be adapted to the requested format."""


def adapt_package(package):
    """Adapts ``.epub.Package`` to a ``BinderItem`` and cascades
    the adaptation downward to ``DocumentItem``
    and ``ResourceItem``.
    The results of this process provide the same interface as
    ``.models.Binder``, ``.models.Document`` and ``.models.Resource``.
    """
    navigation_item = package.navigation
    html = etree.parse(navigation_item.data)
    tree = parse_navigation_html_to_tree(html, navigation_item.name)
    return _node_to_model(tree, package)


def adapt_item(item, package, filename=None):
    """Adapts ``.epub.Item`` to a ``DocumentItem``.

    """
    if item.media_type == 'application/xhtml+xml':
        try:
            html = etree.parse(item.data)
        except Exception as exc:
            logger.error("failed parsing {}".format(item.name))
            raise
        metadata = DocumentPointerMetadataParser(
            html, raise_value_error=False)()
        item.data.seek(0)
        if metadata.get('is_document_pointer'):
            model = DocumentPointerItem(item, package)
        else:
            model = DocumentItem(item, package)
    else:
        model = Resource(item.name, item.data, item.media_type,
                         filename or item.name)
    return model


def make_epub(binders, file):
    """Creates an EPUB file from a binder(s)."""
    if not isinstance(binders, (list, set, tuple,)):
        binders = [binders]
    epub = EPUB([_make_package(binder) for binder in binders])
    epub.to_file(epub, file)


def make_publication_epub(binders, publisher, publication_message, file):
    """Creates an epub file from a binder(s). Also requires
    publication information, meant to be used in a EPUB publication
    request.
    """
    if not isinstance(binders, (list, set, tuple,)):
        binders = [binders]
    packages = []
    for binder in binders:
        metadata = binder.metadata
        binder.metadata = deepcopy(metadata)
        binder.metadata.update({'publisher': publisher,
                                'publication_message': publication_message})
        packages.append(_make_package(binder))
        binder.metadata = metadata
    epub = EPUB(packages)
    epub.to_file(epub, file)


def get_model_extensions(binder):
    extensions = {}
    # Set model identifier file extensions.
    for model in flatten_model(binder):
        if isinstance(model, (Binder, TranslucentBinder,)):
            continue
        ext = mimetypes.guess_extension(model.media_type, strict=False)
        if ext is None:
            raise ValueError("Can't apply an extension to media-type '{}'."
                             .format(model.media_type))
        extensions[model.id] = ext
        extensions[model.ident_hash] = ext
    return extensions


def _make_package(binder):
    """Makes an ``.epub.Package`` from a  Binder'ish instance."""
    package_id = binder.id
    if package_id is None:
        package_id = hash(binder)

    package_name = "{}.opf".format(package_id)

    extensions = get_model_extensions(binder)

    template_env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)

    # Build the package item list.
    items = []
    # Build the binder as an item, specifically a navigation item.
    navigation_document = bytes(HTMLFormatter(binder, extensions))
    navigation_document_name = "{}{}".format(
        package_id,
        mimetypes.guess_extension('application/xhtml+xml', strict=False))
    item = Item(str(navigation_document_name),
                io.BytesIO(navigation_document),
                'application/xhtml+xml',
                is_navigation=True, properties=['nav'])
    items.append(item)
    resources = {}
    # Roll through the model list again, making each one an item.
    for model in flatten_model(binder):
        for resource in getattr(model, 'resources', []):
            resources[resource.id] = resource
            with resource.open() as data:
                item = Item(resource.id, data, resource.media_type)
            items.append(item)

        if isinstance(model, (Binder, TranslucentBinder,)):
            continue
        if isinstance(model, DocumentPointer):
            content = bytes(HTMLFormatter(model))
            item = Item(''.join([model.ident_hash, extensions[model.id]]),
                        io.BytesIO(content),
                        model.media_type)
            items.append(item)
            continue
        for reference in model.references:
            if reference.remote_type == INLINE_REFERENCE_TYPE:
                # has side effects - converts ref type to INTERNAL w/
                # appropriate uri, so need to replicate resource treatment from
                # above
                resource = _make_resource_from_inline(reference)
                model.resources.append(resource)
                resources[resource.id] = resource
                with resource.open() as data:
                    item = Item(resource.id, data, resource.media_type)
                items.append(item)
                reference.bind(resource, '../resources/{}')

            elif reference.remote_type == INTERNAL_REFERENCE_TYPE:
                filename = os.path.basename(reference.uri)
                resource = resources.get(filename)
                if resource:
                    reference.bind(resource, '../resources/{}')

        complete_content = bytes(HTMLFormatter(model))
        item = Item(''.join([model.ident_hash, extensions[model.id]]),
                    io.BytesIO(complete_content),
                    model.media_type)
        items.append(item)

    # Build the package.
    package = Package(package_name, items, binder.metadata)
    return package


def _make_resource_from_inline(reference):
    """Makes an ``models.Resource`` from a ``models.Reference``
       of type INLINE. That is, a data: uri"""
    uri = DataURI(reference.uri)
    data = io.BytesIO(uri.data)
    mimetype = uri.mimetype
    res = Resource('dummy', data, mimetype)
    res.id = res.filename
    return res


def _make_item(model):
    """Makes an ``.epub.Item`` from
    a ``.models.Document`` or ``.models.Resource``
    """
    item = Item(model.id, model.content, model.media_type)
    return item


def _node_to_model(tree_or_item, package, parent=None,
                   lucent_id=TRANSLUCENT_BINDER_ID):
    """Given a tree, parse to a set of models"""
    if 'contents' in tree_or_item:
        # It is a binder.
        tree = tree_or_item
        # Grab the package metadata, so we have required license info
        metadata = package.metadata.copy()
        if tree['id'] == lucent_id:
            metadata['title'] = tree['title']
            binder = TranslucentBinder(metadata=metadata)
        else:
            try:
                package_item = package.grab_by_name(tree['id'])
                binder = BinderItem(package_item, package)
            except KeyError:  # Translucent w/ id
                metadata.update({
                   'title': tree['title'],
                   'cnx-archive-uri': tree['id'],
                   'cnx-archive-shortid': tree['shortId']})
                binder = Binder(tree['id'], metadata=metadata)
        for item in tree['contents']:
            node = _node_to_model(item, package, parent=binder,
                                  lucent_id=lucent_id)
            if node.metadata['title'] != item['title']:
                binder.set_title_for_node(node, item['title'])
        result = binder
    else:
        # It is a document.
        item = tree_or_item
        package_item = package.grab_by_name(item['id'])
        result = adapt_item(package_item, package)
    if parent is not None:
        parent.append(result)
    return result


def _id_from_metadata(metadata):
    """Given an item's metadata, discover the id."""
    # FIXME Where does the system identifier come from?
    system = 'cnx-archive'
    identifier = "{}-uri".format(system)
    return metadata.get(identifier)


class BinderItem(Binder):

    def __init__(self, item, package):
        self._item = item
        self._package = package
        html = etree.parse(self._item.data)
        metadata = parse_metadata(html)
        resources = [
            adapt_item(package.grab_by_name(resource['id']),
                       package, resource['filename'])
            for resource in parse_resources(html)]
        id = _id_from_metadata(metadata)
        super(BinderItem, self).__init__(
            id, metadata=metadata, resources=resources)


class DocumentPointerItem(DocumentPointer):

    def __init__(self, item, package):
        self._item = item
        self._package = package
        self._html = etree.parse(self._item.data)

        metadata = DocumentPointerMetadataParser(self._html)()
        id = _id_from_metadata(metadata)
        super(DocumentPointerItem, self).__init__(id, metadata=metadata)


class DocumentItem(Document):

    def __init__(self, item, package):
        self._item = item
        self._package = package
        self._html = etree.parse(self._item.data)

        metadata = parse_metadata(self._html)
        body = self._html.xpath('//xhtml:body',
                                namespaces=HTML_DOCUMENT_NAMESPACES)[0]
        metadata_nodes = self._html.xpath(
                                    "//xhtml:body/*[@data-type='metadata']",
                                    namespaces=HTML_DOCUMENT_NAMESPACES)
        for node in metadata_nodes:
            body.remove(node)
        for key in body.keys():
            if key in ('itemtype', 'itemscope'):
                body.attrib.pop(key)

        content = etree.tostring(self._html)

        id = _id_from_metadata(metadata)
        resources = None
        super(DocumentItem, self).__init__(id, content, metadata)

        # Based on the reference list, make a best effort
        # to acquire resources.
        resources = []
        for ref in self.references:
            if ref.remote_type == 'external':
                continue
            elif not ref.uri.find('../resources') >= 0:
                continue
            name = os.path.basename(ref.uri)
            try:
                resource = adapt_item(package.grab_by_name(name), package)
                ref.bind(resource, '../resources/{}')
                resources.append(resource)
            except KeyError:
                # When resources are missing, the problem is pushed off
                # to the rendering process, which will
                # raise a missing reference exception when necessary.
                pass
        self.resources = resources


def adapt_single_html(html):
    """Adapts a single html document generated by
    ``.formatters.SingleHTMLFormatter`` to a ``models.Binder``
    """
    html_root = etree.fromstring(html)

    metadata = parse_metadata(html_root.xpath('//*[@data-type="metadata"]')[0])
    id_ = metadata['cnx-archive-uri'] or 'book'

    binder = Binder(id_, metadata=metadata)
    nav_tree = parse_navigation_html_to_tree(html_root, id_)

    body = html_root.xpath('//xhtml:body', namespaces=HTML_DOCUMENT_NAMESPACES)
    _adapt_single_html_tree(binder, body[0], nav_tree, top_metadata=metadata)

    return binder


def _adapt_single_html_tree(parent, elem, nav_tree, top_metadata,
                            id_map=None, depth=0):
    title_overrides = [i.get('title') for i in nav_tree['contents']]

    # A dictionary to allow look up of a document and new id using the old html
    # element id

    if id_map is None:
        id_map = {}

    def fix_generated_ids(page, id_map):
        """Fix element ids (remove auto marker) and populate id_map."""

        content = content_to_etree(page.content)

        new_ids = []
        for element in content.xpath('.//*[@id]'):
            id_val = element.get('id')
            if id_val.startswith('auto_'):
                new_val = id_val.split('_', 2)[-1]
                # Did content from different pages w/ same original id
                # get moved to the same page?
                if new_val in new_ids:
                    suffix = 0
                    while (new_val + str(suffix)) in new_ids:
                        suffix += 1
                    new_val = new_val + str(suffix)
            else:
                new_val = id_val
            new_ids.append(new_val)
            element.set('id', new_val)
            id_map['#{}'.format(id_val)] = (page, new_val)

        id_map['#{}'.format(page.id)] = (page, '')
        if page.id and '@' in page.id:
            id_map['#{}'.format(page.id.split('@')[0])] = (page, '')

        page.content = etree_to_content(content)

    def fix_links(page, id_map):
        """Remap all intra-book links, replace with value from id_map."""

        content = content_to_etree(page.content)
        for i in content.xpath('.//*[starts-with(@href, "#")]',
                               namespaces=HTML_DOCUMENT_NAMESPACES):
            ref_val = i.attrib['href']
            if ref_val in id_map:
                target_page, target = id_map[ref_val]
                if page == target_page:
                        i.attrib['href'] = '#{}'.format(target)
                else:
                    target_id = target_page.id.split('@')[0]
                    if not target:  # link to page
                        i.attrib['href'] = '/contents/{}'.format(target_id)
                    else:
                        i.attrib['href'] = '/contents/{}#{}'.format(
                            target_id, target)
            else:
                logger.error('Bad href: {}'.format(ref_val))

        page.content = etree_to_content(content)

    def _compute_id(p, elem, key):
        """Compute id and shortid from parent uuid and child attr"""
        p_ids = [p.id.split('@')[0]]
        if 'cnx-archive-uri' in p.metadata and p.metadata['cnx-archive-uri']:
            p_ids.insert(0, p.metadata['cnx-archive-uri'].split('@')[0])

        for p_id in p_ids:
            try:
                p_uuid = uuid.UUID(p_id)
                break
            except ValueError:
                pass
        else:  # Punt - no parent uuid, make one up for child
            return str(uuid.uuid4())

        uuid_key = elem.get('data-uuid-key', elem.get('class', key))
        return str(uuid.uuid5(p_uuid, uuid_key))

    def _compute_shortid(ident_hash):
        """Compute shortId from uuid or ident_hash"""
        ver = None
        if '@' in ident_hash:
            (id_str, ver) = ident_hash.split('@')
        else:
            id_str = ident_hash
        try:
            id_uuid = uuid.UUID(id_str)
        except ValueError:
            # id is not a uuid, no shortid
            return None

        shortid = (base64.urlsafe_b64encode(id_uuid.bytes)[:8]).decode('utf-8')
        if ver:
            return '@'.join((shortid, ver))
        else:
            return shortid

    # Adapt each <div data-type="unit|chapter|page|composite-page"> into
    # translucent binders, documents and composite documents
    for child in elem.getchildren():
        data_type = child.attrib.get('data-type')

        if data_type in ('unit', 'chapter', 'composite-chapter',
                         'page', 'composite-page'):
            # metadata munging for all node types, in one place
            metadata = parse_metadata(
                    child.xpath('./*[@data-type="metadata"]')[0])

            # Handle version, id and uuid from metadata
            if not metadata.get('version'):
                if data_type.startswith('composite-'):
                    if top_metadata.get('version') is not None:
                        metadata['version'] = top_metadata['version']
                elif parent.metadata.get('version') is not None:
                    metadata['version'] = parent.metadata['version']

            id_ = metadata.get('cnx-archive-uri') or child.attrib.get('id')
            if not id_:
                id_ = _compute_id(parent, child, metadata.get('title'))
                if metadata.get('version'):
                    metadata['cnx-archive-uri'] = \
                        '@'.join((id_, metadata['version']))
                else:
                    metadata['cnx-archive-uri'] = id_
                metadata['cnx-archive-shortid'] = None

            if (metadata.get('cnx-archive-uri') and
                    not metadata.get('cnx-archive-shortid')):
                metadata['cnx-archive-shortid'] = \
                        _compute_shortid(metadata['cnx-archive-uri'])

            shortid = metadata.get('cnx-archive-shortid')

        if data_type in ['unit', 'chapter', 'composite-chapter']:
            # All the non-leaf node types
            title = lxml.html.HtmlElement(
                        child.xpath('*[@data-type="document-title"]',
                                    namespaces=HTML_DOCUMENT_NAMESPACES)[0]
                        ).text_content().strip()
            metadata.update({'title': title,
                             'id': id_,
                             'shortId': shortid,
                             'type': data_type})
            binder = Binder(id_, metadata=metadata)
            # Recurse
            _adapt_single_html_tree(binder, child,
                                    nav_tree['contents'].pop(0),
                                    top_metadata=top_metadata,
                                    id_map=id_map, depth=depth+1)
            parent.append(binder)
        elif data_type in ['page', 'composite-page']:
            # Leaf nodes
            nav_tree['contents'].pop(0)
            metadata_nodes = child.xpath("*[@data-type='metadata']",
                                         namespaces=HTML_DOCUMENT_NAMESPACES)
            for node in metadata_nodes:
                child.remove(node)
            for key in child.keys():
                if key in ('itemtype', 'itemscope'):
                    child.attrib.pop(key)

            contents = etree.tostring(child)
            model = {
                'page': Document,
                'composite-page': CompositeDocument,
                }[child.attrib['data-type']]

            document = model(id_, contents, metadata=metadata)
            parent.append(document)

            fix_generated_ids(document, id_map)  # also populates id_map
        elif data_type in ['metadata', None]:
            # Expected non-nodal child types
            pass
        else:  # Fall through - child is not a defined type
            raise AdaptationError('Unknown data-type for child node')

    # Assign title overrides
    if len(parent) != len(title_overrides):
        logger.error('Skipping title overrides -'
                     'mismatched numbers: parent: {}, titles: {}'.format(
                         len(parent), len(title_overrides)))
        raise AdaptationError('Nav TOC does not match HTML structure')

    for i, node in enumerate(parent):
        parent.set_title_for_node(node, title_overrides[i])

    # only fixup links after all pages
    # processed for whole book, to allow for foward links
    if depth == 0:
        for page in flatten_to_documents(parent):
            fix_links(page, id_map)
