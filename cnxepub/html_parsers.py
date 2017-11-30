# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import re

from lxml import etree

from .models import TRANSLUCENT_BINDER_ID


HTML_DOCUMENT_NAMESPACES = {
    'xhtml': "http://www.w3.org/1999/xhtml",
    'epub': "http://www.idpf.org/2007/ops",
    }


def _squash_to_text(elm, remove_namespaces=False):
    value = [elm.text or '']
    for child in elm.getchildren():
        value.append(etree.tostring(child).decode('utf-8').strip())
        value.append(child.tail or '')
    if remove_namespaces:
        value = [re.sub(' xmlns:?[^=]*="[^"]*"', '', v) for v in value]
    value = ''.join(value)
    return value


def parse_navigation_html_to_tree(html, id):
    """Parse the given ``html`` (an etree object) to a tree.
    The ``id`` is required in order to assign the top-level tree id value.
    """
    def xpath(x):
        return html.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    try:
        value = xpath('//*[@data-type="binding"]/@data-value')[0]
        is_translucent = value == 'translucent'
    except IndexError:
        is_translucent = False
    if is_translucent:
        id = TRANSLUCENT_BINDER_ID
    tree = {'id': id,
            'title': xpath('//*[@data-type="document-title"]/text()')[0],
            'contents': [x for x in _nav_to_tree(xpath('//xhtml:nav')[0])]
            }
    return tree


def _nav_to_tree(root):
    """Given an etree containing a navigation document structure
    rooted from the 'nav' element, parse to a tree:
    {'id': <id>|'subcol', 'title': <title>, 'contents': [<tree>, ...]}
    """
    def expath(e, x):
        return e.xpath(x, namespaces=HTML_DOCUMENT_NAMESPACES)
    for li in expath(root, 'xhtml:ol/xhtml:li'):
        is_subtree = bool([e for e in li.getchildren()
                           if e.tag[e.tag.find('}')+1:] == 'ol'])
        if is_subtree:
            # It's a sub-tree and have a 'span' and 'ol'.
            itemid = li.get('cnx-archive-uri', 'subcol')
            shortid = li.get('cnx-archive-shortid')
            yield {'id': itemid,
                   # Title is wrapped in a span, div or some other element...
                   'title': _squash_to_text(expath(li, '*')[0],
                                            remove_namespaces=True),
                   'shortId': shortid,
                   'contents': [x for x in _nav_to_tree(li)],
                   }
        else:
            # It's a node and should only have an li.
            a = li.xpath('xhtml:a', namespaces=HTML_DOCUMENT_NAMESPACES)[0]
            yield {'id': a.get('href'),
                   'shortid': li.get('cnx-archive-shortid'),
                   'title': _squash_to_text(a, remove_namespaces=True)}


def parse_metadata(html):
    """Parse metadata out of the given an etree object as ``html``."""
    parser = DocumentMetadataParser(html)
    return parser()


def parse_resources(html):
    """Return a list of resource names found in the html metadata section."""
    xpath = '//*[@data-type="resources"]//xhtml:li/xhtml:a'
    for resource in html.xpath(xpath, namespaces=HTML_DOCUMENT_NAMESPACES):
        yield {
            'id': resource.get('href'),
            'filename': resource.text.strip(),
            }


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
        'publishers', 'copyright_holders', 'authors', 'summary',
        'cnx-archive-uri', 'cnx-archive-shortid', 'derived_from_uri',
        'derived_from_title', 'print_style', 'version',
        )

    def __init__(self, elm_tree, raise_value_error=True):
        self._xml = elm_tree
        self.raise_value_error = raise_value_error

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
                value = getattr(self, key.replace('-', '_'))
                if self.raise_value_error and \
                        key in self.metadata_required_keys and value is None:
                    raise ValueError(
                        "A value for '{}' could not be found.".format(key))
                items[key] = value
        return items

    @property
    def title(self):
        items = self.parse('.//*[@data-type="document-title"]/text()')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def summary(self):
        items = self.parse('.//*[@data-type="description"]')
        try:
            description = items[0]
            value = _squash_to_text(description).encode('utf-8')
        except IndexError:
            value = None
        return value

    @property
    def created(self):
        items = self.parse('.//xhtml:meta[@itemprop="dateCreated"]/@content')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def revised(self):
        items = self.parse('.//xhtml:meta[@itemprop="dateModified"]/@content')
        try:
            value = items[0]
        except IndexError:
            value = None
        return value

    @property
    def language(self):
        # look for lang attribute or schema.org meta tag
        items = self.parse('ancestor-or-self::*/@lang'
                           ' | ancestor-or-self::*/*'
                           '[@data-type="language"]/@content'
                           )
        try:
            value = items[-1]  # nodes returned in tree order, we want nearest
        except IndexError:
            value = None
        return value

    @property
    def subjects(self):
        items = self.parse('.//xhtml:*[@data-type="subject"]/text()')
        return items

    @property
    def keywords(self):
        items = self.parse('.//xhtml:*[@data-type="keyword"]/text()')
        return items

    @property
    def license_url(self):
        # Three cases for location of metadata stanza:
        #  1. direct child of current node
        #  2. direct child of any ancestor
        #  3. Top of book (occurs when fetching from root)
        items = self.parse('ancestor-or-self::*/*[@data-type="metadata"]//*'
                           '[@data-type="license"]/@href'
                           ' | /xhtml:html/xhtml:body/*'
                           '[@data-type="metadata"]//*'
                           '[@data-type="license"]/@href'
                           )

        try:
            value = items[-1]  # doc order, want lowest (nearest)
        except IndexError:
            value = None
        return value

    @property
    def license_text(self):
        # Same as license_url
        items = self.parse('ancestor-or-self::*/*[@data-type="metadata"]//*'
                           '[@data-type="license"]/text()'
                           ' | /xhtml:html/xhtml:body/*'
                           '[@data-type="metadata"]//*'
                           '[@data-type="license"]/text()'
                           )
        try:
            value = items[-1]
        except IndexError:
            value = None
        return value

    def _parse_person_info(self, xpath):
        unordered = []
        for elm in self.parse(xpath):
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
            refines_xpath_tmplt = """\
.//xhtml:meta[@refines="#{}" and @property="display-seq"]/@content"""
            if elm_id is not None:
                try:
                    order = self.parse(refines_xpath_tmplt.format(elm_id))[0]
                except IndexError:
                    order = 0  # Check for refinement failed, use constant
            unordered.append((order, person,))
        ordered = sorted(unordered, key=lambda x: x[0])
        values = [x[1] for x in ordered]
        return values

    @property
    def publishers(self):
        xpath = './/xhtml:*[@data-type="publisher"]'
        return self._parse_person_info(xpath)

    @property
    def editors(self):
        xpath = './/xhtml:*[@data-type="editor"]'
        return self._parse_person_info(xpath)

    @property
    def illustrators(self):
        xpath = './/xhtml:*[@data-type="illustrator"]'
        return self._parse_person_info(xpath)

    @property
    def translators(self):
        xpath = './/xhtml:*[@data-type="translator"]'
        return self._parse_person_info(xpath)

    @property
    def copyright_holders(self):
        xpath = './/xhtml:*[@data-type="copyright-holder"]'
        return self._parse_person_info(xpath)

    @property
    def authors(self):
        xpath = './/xhtml:*[@data-type="author"]'
        return self._parse_person_info(xpath)

    @property
    def cnx_archive_uri(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-uri"]/@data-value')
        if items:
            return items[0]

    @property
    def cnx_archive_shortid(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-shortid"]/@data-value')
        if items:
            return items[0]

    @property
    def version(self):
        items = self.parse(
            './/xhtml:*[@data-type="cnx-archive-uri"]/@data-value')
        if items:
            if '@' in items[0]:
                return items[0].split('@')[1]

    @property
    def derived_from_uri(self):
        items = self.parse('.//xhtml:*[@data-type="derived-from"]/@href')
        if items:
            return items[0]

    @property
    def print_style(self):
        items = self.parse('.//xhtml:*[@data-type="print-style"]/text()')
        if items:
            return items[0]

    @property
    def derived_from_title(self):
        items = self.parse('.//xhtml:*[@data-type="derived-from"]/text()')
        if items:
            return items[0]


class DocumentPointerMetadataParser(DocumentMetadataParser):
    metadata_required_keys = (
            'title', 'cnx-archive-uri', 'is_document_pointer',
            )
    metadata_optional_keys = DocumentMetadataParser.metadata_optional_keys + (
            'license_url', 'summary', 'cnx-archive-shortid',
            )

    @property
    def is_document_pointer(self):
        items = self.parse('.//xhtml:*[@data-type="document"]/@data-value')
        if items:
            return items[0] == 'pointer'
