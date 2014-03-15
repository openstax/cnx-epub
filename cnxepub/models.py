# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import io
import hashlib
try:
    from collections.abc import MutableSequence
except ImportError:
    from collections import MutableSequence


__all__ = ('Binder', 'TranslucentBinder', 'Document', 'Resource',)


RESOURCE_HASH_TYPE = 'md5'
TRANSLUCENT_BINDER_ID = 'subcol'


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


def flatten_tree_to_ident_hashs(item_or_tree, lucent_id=TRANSLUCENT_BINDER_ID):
    """Flatten a tree to id and version values (ident_hash)."""
    if 'contents' in item_or_tree:
        tree = item_or_tree
        if tree['id'] != lucent_id:
            yield tree['id']
        for i in tree['contents']:
            ##yield from flatten_tree_to_ident_hashs(i, lucent_id)
            for x in flatten_tree_to_ident_hashs(i, lucent_id):
                yield x
    else:
        item = item_or_tree
        yield item['id']
    raise StopIteration()


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
        self.metadata = metadata or {}
        if title_overrides is not None:
            if len(self._nodes) != len(title_overrides):
                raise ValueError(
                    "``title_overrides`` should be the same length as "
                    "``nodes``. {} != {}" \
                    .format(len(self._nodes), len(title_overrides)))
            self._title_overrides = title_overrides
        else:
            self._title_overrides = [None] * len(self._nodes)

    @property
    def ident_hash(self):
        return None

    def get_uri(self, system, default=None):
        return None

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


##class Document:
class Document(object):
    """An HTML document noted as ``content`` on the instance,
    which can contain ``Resource`` instances.
    """

    def __init__(self, id, content, metadata=None, resources=None):
        self.id = id
        valid_data_types = (io.StringIO, io.BytesIO,)
        if not isinstance(content, valid_data_types):
            types = ' or '.join([str(x) for x in valid_data_types]),
            raise ValueError("Content must be an {} instance. "
                             "'{}' was given." \
                             .format(types, type(content)))
        self.content = content
        self.metadata = metadata or {}
        self.resources = resources or []

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


class Resource:
    """A binary object used within the context of the ``Document``.
    It is typically referenced within the documents HTML content.
    """

    def __init__(self, id, data, media_type, filename=None):
        self.id = id
        if not isinstance(content, io.BytesIO):
            raise ValueError("Data must be an io.BytesIO instance. "
                             "'{}' was given.".format(type(data)))
        self.data = data
        self.media_type = media_type
        self.filename = filename or ''

        self._hash = hashlib.new(RESOURCE_HASH_TYPE,
                                 self.data.read()).hexdigest()
        self.data.seek(0)

    @property
    def hash(self):
        return self._hash
