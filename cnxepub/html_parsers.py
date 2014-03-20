# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from lxml import etree

from .models import TRANSLUCENT_BINDER_ID


HTML_DOCUMENT_NAMESPACES = {
    'xhtml': "http://www.w3.org/1999/xhtml",
    'epub': "http://www.idpf.org/2007/ops",
    }


def parse_navigation_html_to_tree(html, id):
    """Parse the given ``html`` (an etree object) to a tree.
    The ``id`` is required in order to assign the top-level tree id value.
    """
    xpath = lambda x: html.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    try:
        value = xpath('//*[@data-type="binding"]/@data-value')[0]
        is_translucent = value == 'translucent'
    except IndexError:
        is_translucent = False
    if is_translucent:
        id = TRANSLUCENT_BINDER_ID
    tree = {'id': id,
            'title': xpath('//*[@data-type="title"]/text()')[0],
            'contents': [x for x in _nav_to_tree(xpath('//xhtml:nav')[0])]
            }
    return tree


def _nav_to_tree(root):
    """Given an etree containing a navigation document structure
    rooted from the 'nav' element, parse to a tree:
    {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}
    """
    expath = lambda e,x: e.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    for li in expath(root, 'xhtml:ol/xhtml:li'):
        classes = li.get('class', '').split()
        is_subtree = bool([e for e in li.getchildren()
                           if e.tag[e.tag.find('}')+1:] == 'ol'])
        if is_subtree:
            # It's a sub-tree and have a 'span' and 'ol'.
            yield {'id': 'subcol', # Special id...
                   'title': expath(li, 'xhtml:span/text()')[0],
                   'contents': [x for x in _nav_to_tree(li)],
                   }
        else:
            # It's a node and should only have an li.
            a = li.xpath('xhtml:a', namespaces=HTML_DOCUMENT_NAMESPACES)[0]
            yield {'id': a.get('href'), 'title': a.text}
    raise StopIteration()


def parse_metadata(html):
    """Parse metadata out of the given an etree object as ``html``."""
    parser = DocumentMetadataParser(html)
    return parser()


class DocumentMetadataParser:
    """Given a file-like object, parse out the metadata to a dictionary.
    This only parses the data. It does not validate it.
    """
    namespaces = HTML_DOCUMENT_NAMESPACES
    metadata_required_keys = (
        'title', 'license_url',
        )
    metadata_optional_keys = (
        'created', 'revised', 'language', 'subjects', 'keywords',
        'license_text', 'editors', 'illustrators', 'translators',
        'publishers', 'copyright_holders', 'authors',
        )

    def __init__(self, elm_tree):
       self._xml = elm_tree

    def __call__(self):
        return self.metadata

    def parse(self, xpath, prefix=""):
        values = self._xml.xpath(prefix + xpath,
                                 namespaces=self.namespaces)
        return values

    @property
    def metadata(self):
        items = {}
        keyrings = (self.metadata_required_keys, self.metadata_optional_keys,)
        for keyring in keyrings:
            for key in keyring:
                # TODO On refactoring properties
                # raise an error on property access rather than outside of it
                # as is currently being done here.
                value = getattr(self, key)
                if key in self.metadata_required_keys and value is None:
                    raise ValueError(
                        "A value for '{}' could not be found.".format(key))
                elif value is None:
                    continue
                items[key] = value
        return items

    @property
    def title(self):
        items = self.parse('//xhtml:*[@data-type="title"]/text()')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def created(self):
        items = self.parse('//xhtml:meta[@itemprop="dateCreated"]/@content')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def revised(self):
        items = self.parse('//xhtml:meta[@itemprop="dateModified"]/@content')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def language(self):
        items = self.parse('//xhtml:*[@data-type="language"]/text()')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def subjects(self):
        items = self.parse('//xhtml:*[@data-type="subject"]/text()')
        return items

    @property
    def keywords(self):
        items = self.parse('//xhtml:*[@data-type="keyword"]/text()')
        return items

    @property
    def license_url(self):
        items = self.parse('//xhtml:*[@data-type="license"]/@href')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def license_text(self):
        items = self.parse('//xhtml:*[@data-type="license"]/text()')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def publishers(self):
        items = self.parse('//xhtml:*[@data-type="publisher"]/@content')
        return items

    @property
    def editors(self):
        items = self.parse('//xhtml:*[@data-type="editor"]/@content')
        return items

    @property
    def illustrators(self):
        items = self.parse('//xhtml:*[@data-type="illustrator"]/@content')
        return items

    @property
    def translators(self):
        items = self.parse('//xhtml:*[@data-type="translator"]/@content')
        return items

    @property
    def copyright_holders(self):
        items = self.parse('//xhtml:*[@data-type="copyright-holders"]/@content')
        return items

    @property
    def authors(self):
        unordered = []
        for elm in self.parse('//xhtml:*[@data-type="author"]'):
            elm_id = elm.get('id', None)
            if len(elm) > 0:
                person_elm = elm[0]
                name = person_elm.text
                type_ = person_elm.get('data-type', None)
                id_ = person_elm.get('href', None)
            else:
                name = elm.text
                type_ = None
                id_ = None
            person = {'name': name, 'type': type_, 'id': id_}
            # Meta refinement allows these to be ordered.
            order = None
            if elm_id is not None:
                try:
                    order = self.parse('//xhtml:meta[@refines="#{}" and @property="display-seq"]/@content'.format(elm_id))[0]
                except IndexError:
                    pass # Check for refinement failed, maintain None value.
            unordered.append((order, person,))
        ordered = sorted(unordered, key=lambda x: x[0])
        values = [x[1] for x in ordered]
        return values
