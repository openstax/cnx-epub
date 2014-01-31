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
from collections import Container, Iterator, MutableSequence

from lxml import etree


EPUB_CONTAINER_XML_RELATIVE_PATH = "META-INF/container.xml"
EPUB_CONTAINER_XML_NAMESPACES = {
    'ns': "urn:oasis:names:tc:opendocument:xmlns:container"
    }
EPUB_OPF_NAMESPACES = {
    'opf': "http://www.idpf.org/2007/opf",
    'dc': "http://purl.org/dc/elements/1.1/",
    }


class EPUB(MutableSequence):
    """EPUB3 format"""

    def __init__(self):
        self._packages = []

    @classmethod
    def from_file(cls, filepath):
        """Create the object from file."""
        # Extract the epub to the current working directory.
        with zipfile.ZipFile(filepath) as zf:
            zf.extractall()
        
        # Build a blank epub object then parse the packages.
        container_xml_filepath = os.path.join(os.getcwd(),
                                              EPUB_CONTAINER_XML_RELATIVE_PATH)
        container_xml = etree.parse(container_xml_filepath)

        epub = cls()
        for pkg in container_xml.xpath('//ns:rootfile/@full-path',
                                       namespaces=EPUB_CONTAINER_XML_NAMESPACES):
            epub.append(EPUBPackage.from_file(pkg))
        return epub

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

    def __init__(self, metadata={}, items=[], spine_order=None):
        # TODO Metadata will become a mutable sequence object.
        self.metadata = metadata
        self._items = items
        self._spine_indexes = spine_order  # TODO Ordered reference object, similar to nav.

    @classmethod
    def from_file(cls, filepath):
        """Create the object from a file."""
        opf_xml = etree.parse(filepath)
        package_relative_root = os.path.abspath(os.path.dirname(filepath))
        # FIXME Incomplete metadata extraction.
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

        # FIXME Ignoring spine ordering, because I (pumazi) don't understand
        #       parts of it.
        spine_items = opf_xml.xpath('/opf:package/opf:spine/opf:itemref',
                                    namespaces=EPUB_OPF_NAMESPACES)
        return package

    @property
    def navigation(self):
        navs = [i for i in self._items if i.is_navigation]
        if len(navs) > 1:
            pass # FIXME This can't happen.
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
