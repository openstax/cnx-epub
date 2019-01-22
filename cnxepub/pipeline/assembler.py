import os

from lxml import etree

from ..models import Binder, TranslucentBinder, Document
from ..formatters import SingleHTMLFormatter


__all__ = (
    'assemble_collection_html',
    'Adapter',
)


def assemble_collection_html(out_fname='ITWORKS', out_dir='.'):
    # Locate collxml
    # TODO: ... what if it can't be found?
    collxml_path = os.path.join('col11562_1.23_complete', 'collection.xml')
    out_fname += '.xhtml'

    binder = collxml_to_binder(collxml_path)

    out_dir = os.path.join(out_dir, out_fname)

    print('\nWriting to {}\n...'.format(out_fname))
    with open(out_dir, 'w') as f:
        f.write(str(SingleHTMLFormatter(binder)))


def collxml_to_binder(collxml_path):
    tags = [
        '{http://cnx.rice.edu/collxml}subcollection',
        '{http://cnx.rice.edu/collxml}collection',
        '{http://cnx.rice.edu/collxml}module',
        '{http://cnx.rice.edu/mdml}title',
    ]

    collxml_etree = etree.iterparse(collxml_path, events=('start', 'end'),
                                    tag=tags, remove_blank_text=True)

    root_adapter = build_adapters_tree(collxml_etree)

    binder = root_adapter.to_model()
    return binder


def build_adapters_tree(collxml_etree):
    """Binders require bottom-up construction (sub-binders are passed into the
    constructor). So we'll (1) parse the element tree top-down and store the
    needed information in Adapter nodes and then (2) use post-order traversal
    on the Adapter tree to construct Binders from their sub-binders.
    """
    node = None  # the node currently being parsed

    for event, element in collxml_etree:
        tag_name = element.tag.split('}')[-1]  # element tag without namespace

        if tag_name == 'title':
            assert node  # adapter with 'collection' tag should already exist
            node.title = element.text

        elif event == 'start':
            new_ = Adapter(tag_name, element.attrib)
            if node:
                node.add_child(new_)
            node = new_

        elif event == 'end':
            node = node.parent

    # After the last `end` event is processed, `node` is the root node
    root_node = node
    return root_node


class Adapter(object):
    def __init__(self, tag, attrib, title=''):
        self.tag = tag
        self.attrib = dict(attrib).copy()
        self.title = title
        self.parent = self
        self.children = []

    def add_child(self, child):
        child.parent = self
        self.children.append(child)
        return self

    def __iter__(self):
        return iter(self.children)

    def iter(self, tag='*'):
        if tag == '*' or self.tag == tag:
            yield self

        for child in self:
            yield from child.iter(tag)

    def to_model(self):
        children_adapters = [child.to_model() for child in self.children]
        meta = {'title': self.title}

        if self.tag == 'collection':
            return Binder(self.title, nodes=children_adapters, metadata=meta)
        elif self.tag == 'subcollection':
            return TranslucentBinder(nodes=children_adapters, metadata=meta)
        elif self.tag == 'module':
            module_id = self.attrib.get('document')
            meta['license_url'] = None  # required by `Document`
            return Document(module_id, find_doc_data(module_id), metadata=meta)
        else:
            raise Exception('unrecognized tag: {}'.format(self.tag))


def find_doc_data(module_id):
    """Locates and reads a cnxml file/module with given `module_id`
    TODO: find module resources
    """
    try:
        fname = 'col11562_1.23_complete/{}/index.cnxml.html'.format(module_id)
        with open(fname, 'rb') as fb:
            doc_data = fb.read()
        return doc_data
    except FileNotFoundError as e:
        # FIXME: write log entry or something
        import pdb; pdb.set_trace()
