# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from .models import (
    Binder, TranslucentBinder,
    Document, Resource,
    TRANSLUCENT_BINDER_ID,
    )
from .html_parsers import parse_metadata, parse_navigation_to_tree


__all__ = (
    'adapt_package',
    'BinderItem',
    'DocumentItem',
    )


def adapt_package(package):
    """Adapts ``.epub.Package`` to a ``BinderItem`` and cascades
    the adaptation downward to ``.models.DocumentItem``
    and ``.models.ResourceItem``.
    The results of this process provide the same interface as
    ``.models.Binder``, ``.models.Document`` and ``.models.Resource``.
    """
    navigation_item = package.navigation
    tree = parse_navigation_to_tree(navigation_item)
    return _node_to_model(tree, package)


def _node_to_model(tree_or_item, package, parent=None,
                   lucent_id=TRANSLUCENT_BINDER_ID):
    """Given a tree, parse to a set of models"""
    if 'contents' in tree_or_item:
        # It is a binder.
        tree = tree_or_item
        if tree['id'] == lucent_id:
            binder = TranslucentBinder(metadata={'title': tree['title']})
        else:
            package_item = package.grab_by_name(tree['id'])
            binder = BinderItem(package_item, package)
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
        result = DocumentItem(package_item, package)
    if parent is not None:
        parent.append(result)
    return result


def _id_from_metadata(metadata):
    """Given an item's metadata, discover the id."""
    # FIXME Where does the system identifier come from?
    system = 'cnx-archive'
    identifier = "{}-uri".format(system)
    if identifier in metadata:
        id = metadata[identifier]
    else:
        id = None
    return id


class BinderItem(Binder):

    def __init__(self, item, package):
        self._item = item
        self._package = package
        metadata = parse_metadata(self._item)
        id = _id_from_metadata(metadata)
        super(BinderItem, self).__init__(id, metadata=metadata)


class DocumentItem(Document):

    def __init__(self, item, package):
        self._item = item
        self._package = package
        metadata = parse_metadata(self._item)
        content = self._item.data
        id = _id_from_metadata(metadata)
        # TODO Resource discovery and setting...
        resources = None
        super(DocumentItem, self).__init__(id, content, metadata,
                                           resources=resources)
