from ..models import Binder, TranslucentBinder, Document
from ..formatters import SingleHTMLFormatter
from ..html_parsers import DocumentMetadataParser
from lxml import etree

from litezip.main import COLLECTION_NSMAP


__all__ = (
    'assemble_collection_html',
    'Adapter',
)


class Adapter(object):
    """Base class for creating an adapter for binders and documents.
    It has tree-like behavior and can contain data coming from an XML file"""

    level = 0

    def __init__(self, tag, title=''):
        self.tag = tag
        self.children = []
        self.parent = None
        self.title = title

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, tag):
        # tag = tag.split('}')[1]  # strip-off namespace
        self._tag = tag

    def __bool__(self):
        return True

    def __len__(self):
        # return len(self.children)
        return len(set(self.iter()))

    def __iter__(self):
        return iter(self.children)

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def to_binder(self):
        self.level += 1
        spacing = ' ' * (self.level * 4)

        children_adapters = [child.to_binder() for child in self]

        if self.tag == 'content':
            return TranslucentBinder(nodes=children_adapters, metadata={'title': self.title})
        elif self.tag == 'subcollection':
            return Binder(self.title, nodes=children_adapters, metadata={'title': self.title})
        elif self.tag == 'module':
            import codecs
            with codecs.open('sample_module_html.cnxml.html', 'rb', encoding='utf-8') as f:
                doc_data = f.read()

            metadata = {'license_url': None, 'title': self.title}
            return Document('TODO: DocumentID', doc_data, metadata=metadata)
        elif self.tag == 'root_binder':
            print('ROOT BINDER')
            return Binder(self.title, nodes=children_adapters, metadata={'title': self.title})
        else:
            import pdb; pdb.set_trace()
            # print('SOME OTHER TAG: '.format(self.tag))
            # raise Exception('Unrecognized tag: {}'.format(self.tag))

def adapters_to_binders(adapters):
    """NOW build proper binders because each adapter should have all necessary data (+ behavior obvs)
    """
    return adapters.to_binder()  # a recursive functionk whose result is a completely built tree of binders ;)


def build_adapters_tree(contents):
    """Build adapters, because we can't yet build proper binders
    """
    root_binder = None
    current_node = None
    depth = 0
    collection_title = None
    parsed_root = False

    for event, element in contents:
        tag_name = element.tag.split('}')[1]

        if event == 'start':
            depth += 1  # TEMP: for pretty printing to the terminal
            spacing = ' ' * (depth * 4)

            if not parsed_root:  # we haven't created the root node
                # Don't create an adapter for the collection's title
                if tag_name == 'title':  # just to make sure, future-proof if we accept new tags.
                    collection_title = element.text
                    continue

                if tag_name == 'content':  # actually THE binder
                    # set the root adapter, should be a ``col:content`` tag
                    root_binder = Adapter('root_binder', title=collection_title)
                    current_node = root_binder
                    parsed_root = True
                print('{}{}'.format(spacing, tag_name))
            else:  # build the tree
                # Don't create an adapter for the titles, just set the prop on
                # the current node instead
                if tag_name == 'title':
                    current_node.title = element.text
                    continue

                # create new adapter
                node = Adapter(tag_name)
                # ... add it as child of current node
                current_node.add_child(node)

                # now change the current node
                current_node = node
                print('{}{}'.format(spacing, tag_name))
        elif event == 'end':
            depth -= 1  # TEMP: for pretty printing to the terminal

            if parsed_root:
                current_node = current_node.parent or root_binder
    return root_binder


# TODO: def main(collection, modules, output):
def assemble_collection_html(collection):
    tags = [
        '{http://cnx.rice.edu/collxml}subcollection',
        '{http://cnx.rice.edu/collxml}module',
        '{http://cnx.rice.edu/mdml}title',
        '{http://cnx.rice.edu/collxml}content',
    ]

    # parser = etree.XMLParser(target=Target(), remove_blank_text=True)
    # contents = etree.XML(collection, parser)

    contents = etree.iterparse(collection, events=('start','end'), tag=tags, remove_blank_text=True)
    adapters_tree = build_adapters_tree(contents)
    root_binder = adapters_to_binders(adapters_tree)

    html_out = open('./IT_WORKS.html', 'w')
    print(str(SingleHTMLFormatter(root_binder)), file=html_out)
    html_out.close()
