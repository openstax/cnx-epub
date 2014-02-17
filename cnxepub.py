# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import os
import sys
import io
import zipfile
import tempfile
from collections import Container, Iterator, MutableSequence

from lxml import etree


EPUB_CONTAINER_XML_RELATIVE_PATH = "META-INF/container.xml"
EPUB_CONTAINER_XML_NAMESPACES = {
    'ns': "urn:oasis:names:tc:opendocument:xmlns:container"
    }
EPUB_OPF_NAMESPACES = {
    'opf': "http://www.idpf.org/2007/opf",
    'dc': "http://purl.org/dc/elements/1.1/",
    'lrmi': "http://lrmi.net/the-specification",
    }
HTML_DOCUMENT_NAMESPACES = {
    'xhtml': "http://www.w3.org/1999/xhtml",
    'epub': "http://www.idpf.org/2007/ops",
    }

DOCUMENT_MIMETYPE = 'application/vnd.org.cnx.module'
COLLECTION_MIMETYPE = 'application/vnd.org.cnx.collection'


class EPUB(MutableSequence):
    """EPUB3 format"""

    def __init__(self):
        self._packages = []

    @classmethod
    def from_filepath(cls, filepath, unpack_dir=None):
        """Create the object from file."""
        if unpack_dir is None:
            unpack_dir = tempfile.mkdtemp()
        # Extract the epub to the current working directory.
        with zipfile.ZipFile(filepath, 'r') as zf:
            zf.extractall(path=unpack_dir)

        # Build a blank epub object then parse the packages.
        container_xml_filepath = os.path.join(unpack_dir,
                                              EPUB_CONTAINER_XML_RELATIVE_PATH)
        container_xml = etree.parse(container_xml_filepath)

        epub = cls()
        for pkg in container_xml.xpath('//ns:rootfile/@full-path',
                                       namespaces=EPUB_CONTAINER_XML_NAMESPACES):
            epub.append(EPUBPackage.from_file(os.path.join(unpack_dir, pkg)))
        return epub

    from_file = from_filepath  # BBB (2014-02-12)

    # ABC methods for MutableSequence
    def __getitem__(self, k):
        return self._packages[k]
    def __setitem__(self, k, v):
        self._packages[k] = v
    def __delitem__(self, k):
        del self._packages[k]
    def __len__(self):
        return len(self._packages)
    def insert(self, k, v):
        self._packages.insert(k, v)


class EPUBPackage(MutableSequence):
    """EPUB3 package"""
    # TODO Navigation document requirement on output/input

    def __init__(self, metadata=None, items=None, spine_order=None):
        self.metadata = metadata or {}
        self._items = []
        if items is not None:
            for item in items:
                self.append(item)

    @classmethod
    def from_filepath(cls, filepath):
        """Create the object from a file."""
        opf_xml = etree.parse(filepath)
        package_relative_root = os.path.abspath(os.path.dirname(filepath))
        md_prefix = "/opf:package/opf:metadata/"
        metadata_xpath = lambda x: opf_xml.xpath(md_prefix+x, namespaces=EPUB_OPF_NAMESPACES)
        metadata = {
            'title': metadata_xpath('dc:title/text()')[0],
            'creator': metadata_xpath('dc:creator/text()')[0],
            'identifier': metadata_xpath('dc:identifier/text()')[0],
            'language': metadata_xpath('dc:language/text()')[0].lower(),
            'publisher': metadata_xpath('dc:publisher/text()')[0],
            'rights': metadata_xpath('dc:rights/text()')[0],
            'license_url': metadata_xpath('opf:link[@rel="cc:license"]/@href')[0],
            'base_attribution_url': metadata_xpath('opf:meta[@property="cc:attributionURL"]/text()')[0],
            'publication_message': metadata_xpath('opf:meta[@property="publicationMessage"]/text()')[0],
            }
        package = cls(metadata)

        # Roll through the item entries
        manifest = opf_xml.xpath('/opf:package/opf:manifest/opf:item',
                                 namespaces=EPUB_OPF_NAMESPACES)
        for item in manifest:
            absolute_filepath = os.path.join(package_relative_root,
                                             item.get('href'))
            properties = item.get('properties', '').split()
            is_navigation = 'nav' in properties
            media_type = item.get('media-type')
            package.append(Item.from_file(absolute_filepath,
                                          media_type=media_type,
                                          is_navigation=is_navigation,
                                          properties=properties))

        # Ignore spine ordering, because it is not important
        #   for our use cases.
        spine_items = opf_xml.xpath('/opf:package/opf:spine/opf:itemref',
                                    namespaces=EPUB_OPF_NAMESPACES)
        return package

    from_file = from_filepath  # BBB (2014-02-12)

    @property
    def navigation(self):
        navs = [i for i in self._items if i.is_navigation]
        if len(navs) == 0:
            raise ValueError("Navigation item not found")
        elif len(navs) > 1:
            raise ValueError("Only one navigation item can exist "
                             "per package. The given value is a second "
                             "navigation item.")
        return navs[0]

    # ABC methods for MutableSequence
    def __getitem__(self, k):
        return self._items[k]
    def __setitem__(self, k, v):
        self._items[k] = v

    def __delitem__(self, k):
        del self._items[k]
    def __len__(self):
        return len(self._items)
    def insert(self, k, v):
        self._items.insert(k, v)

    def grab_by_name(self, name):
        try:
            return [i for i in self._items if i.name == name][0]
        except IndexError:
            raise KeyError("'{}' not found in package.".format(name))


# class EPUBMetadata(MutableMapping):
#     """EPUB3 metadata information"""


class Item(object):
    """Package item"""

    def __init__(self, name, data=None, media_type=None,
                 is_navigation=False, properties=[], **kwargs):
        self.name = name
        self.data = data
        self.media_type = media_type
        self.is_navigation = bool(is_navigation)
        self.properties = properties

    @classmethod
    def from_file(cls, filepath, **kwargs):
        name = os.path.basename(filepath)
        with open(filepath, 'rb') as fb:
            data = io.BytesIO(fb.read())
        return cls(name, data, **kwargs)


def epub_to_mapping(epub):
    package_mappings = []
    for package in epub:
        documents, tree, metadata = _parse_epub_navigation(package.navigation)
        item_mappings = {
            package.navigation.name: {
                'type': COLLECTION_MIMETYPE,
                'metadata': metadata,
                'tree': tree,
                },
            }
        for doc_name in documents:
            doc = package.grab_by_name(doc_name)
            doc_etree = etree.parse(doc.data)
            item_mappings[doc.name] = {
                'type': DOCUMENT_MIMETYPE,
                'metadata': _parse_document_metadata(doc_etree),
                'document': io.BytesIO(etree.tostring(doc_etree)),
                }
        package_mappings.append(item_mappings)
    return package_mappings


def _parse_document_metadata(root):
    """Given an etree element, parse out the metadata to a dictionary.
    This only parses the data. It does not validate it.
    """
    xpath = lambda x: root.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    metadata = {
        'title': xpath('//xhtml:title/text()')[0],
        'language': xpath('//xhtml:meta[@itemprop="inLanguage"]/@content')[0],
        'abstract': etree.tostring(xpath('//xhtml:*[@data-type="description"]')[0]),
        'subjects': [x for x in xpath('//xhtml:*[@data-type="subject"]/@content')],
        'keywords': [x for x in xpath('//xhtml:meta[@data-type="keyword"]/@content')],
        ##'license': xpath('//xhtml:*[@data-type="license"]/@content')[0],
        'license_url': xpath('//xhtml:*[@data-type="license"]/@href')[0],
        'publishers': [x for x in xpath('//xhtml:*[@data-type="publisher"]/@content')],
        'editors': [x for x in xpath('//xhtml:*[@data-type="editor"]/@content')],
        'illustrators': [x for x in xpath('//xhtml:*[@data-type="illustrator"]/@content')],
        'translators': [x for x in xpath('//xhtml:*[@data-type="translator"]/@content')],
        'copyright_holders': [x for x in xpath('//xhtml:*[@data-type="copyright-holder"]/@content')],
        'created': [x for x in xpath('//xhtml:meta[@itemprop="dateCreated"]/@content')][0],
        'revised': [x for x in xpath('//xhtml:meta[@itemprop="dateModified"]/@content')][0],
        }
    unordered = []
    for elm in xpath('//xhtml:*[@data-type="author"]'):
        elm_id = elm.get('id', None)
        uid = elm.get('content', None)
        if len(elm) > 0:
            # Connexions does not accept uids from other identification systems.
            author_elm = elm[0]
            uid = author_elm.text

        order = None
        if elm_id is not None:
            try:
                order = xpath('//xhtml:meta[@refines="#{}" and @property="display-seq"]/@content'.format(elm_id))[0]
            except IndexError:
                pass  # Check for refinement failed, maintain None value.
        unordered.append((order, uid,))
    ordered = sorted(unordered,
                     cmp=lambda x,y: x is None or y is None and -1 or cmp(x,y),
                     key=lambda x: x[0])
    metadata['authors'] = [x[1] for x in ordered]
    return metadata


def _nav_to_tree(root):
    """Given an etree containing a navigation document structure
    rooted from the 'nav' element, parse to a tree:
    {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}
    """
    for li in root.xpath('xhtml:ol/xhtml:li', namespaces=HTML_DOCUMENT_NAMESPACES):
        classes = li.get('class', '').split()
        is_subtree = bool([e for e in li.getchildren()
                           if e.tag[e.tag.find('}')+1:] == 'ol'])
        if is_subtree:
            # It's a sub-tree and have a 'span' and 'ol'.
            yield {'id': 'subcol',  # Special id...
                   'title': li.xpath('xhtml:span/text()',
                                     namespaces=HTML_DOCUMENT_NAMESPACES)[0],
                   'contents': [x for x in _nav_to_tree(li)],
                   }
        else:
            # It's a node and should only have an li.
            a = li.xpath('xhtml:a', namespaces=HTML_DOCUMENT_NAMESPACES)[0]
            yield {'id': a.get('href'), 'title': a.text}
    raise StopIteration()

def _parse_epub_navigation(nav):
    """Parse the navigation items to a name list and tree,
    both of which are using item names as values.
    Returns the name list, tree and document metadaa.
    """
    tree = []
    nav_doc = etree.parse(nav.data)
    nav_metadata = _parse_document_metadata(nav_doc)
    doc_names = [href for href in nav_doc.xpath('//xhtml:nav//xhtml:a/@href', namespaces=HTML_DOCUMENT_NAMESPACES)]
    tree = {'id': nav.name,
            'title': nav_metadata['title'],
            'contents': [x for x in _nav_to_tree(nav_doc.xpath('//xhtml:nav', namespaces=HTML_DOCUMENT_NAMESPACES)[0])]
            }
    return doc_names, tree, nav_metadata
