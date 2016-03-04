# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import os
import io
import logging
import mimetypes
import sys
from copy import deepcopy

import jinja2
from lxml import etree

from .epub import EPUB, Package, Item
from .models import (
    model_to_tree, flatten_model,
    Binder, TranslucentBinder,
    Document, Resource, DocumentPointer,
    TRANSLUCENT_BINDER_ID,
    INTERNAL_REFERENCE_TYPE,
    INLINE_REFERENCE_TYPE,
    )
from .html_parsers import (parse_metadata, parse_navigation_html_to_tree,
                           parse_resources, DocumentPointerMetadataParser,
                           HTML_DOCUMENT_NAMESPACES)

from .data_uri import DataURI


IS_PY3 = sys.version_info.major == 3
logger = logging.getLogger('cnxepub')


__all__ = (
    'adapt_package', 'adapt_item',
    'make_epub', 'make_publication_epub',
    'BinderItem',
    'DocumentItem',
    'DocumentContentFormatter',
    'HTMLFormatter',
    'SingleHTMLFormatter',
    )


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


def adapt_item(item, package):
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
        model = Resource(item.name, item.data, item.media_type, item.name)
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


def _get_model_extensions(binder):
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

    extensions = _get_model_extensions(binder)

    template_env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)

    def isdict(v):
        return isinstance(v, dict)
    template = template_env.from_string(HTML_DOCUMENT,
                                        globals={'isdict': isdict})
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
            adapt_item(package.grab_by_name(name), package)
            for name in parse_resources(html)]
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
        content_xpath = (
            "//xhtml:body/node()[not(self::node()[@data-type='metadata'])]")
        nsmap = {'xhtml': "http://www.w3.org/1999/xhtml"}

        content = io.BytesIO(
            b''.join([
                isinstance(n, str) and n.encode('utf-8') or etree.tostring(n)
                for n in self._html.xpath(content_xpath, namespaces=nsmap)]))
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


class DocumentContentFormatter(object):
    def __init__(self, document):
        self.document = document

    def __unicode__(self):
        return self.__bytes__().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        html = """\
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>{}</body>
</html>""".format(self.document.content)
        return html.encode('utf-8')


class HTMLFormatter(object):
    def __init__(self, model, extensions=None):
        self.model = model
        self.extensions = extensions

    @property
    def _content(self):
        if isinstance(self.model, TranslucentBinder):
            if not self.extensions:
                self.extensions = _get_model_extensions(self.model)
            return tree_to_html(
                model_to_tree(self.model), self.extensions).decode('utf-8')
        elif isinstance(self.model, Document):
            return self.model.content

    @property
    def _template(self):
        if isinstance(self.model, DocumentPointer):
            return jinja2.Template(DOCUMENT_POINTER_TEMPLATE,
                                   trim_blocks=True, lstrip_blocks=True)

        def isdict(v):
            return isinstance(v, dict)

        template_env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
        return template_env.from_string(HTML_DOCUMENT,
                                        globals={'isdict': isdict})

    @property
    def _template_args(self):
        return {
            'metadata': self.model.metadata,
            'content': self._content,
            'is_translucent': getattr(self.model, 'is_translucent', False),
            'resources': getattr(self.model, 'resources', []),
            }

    def __unicode__(self):
        return self.__bytes().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        html = self._template.render(self._template_args)
        return html.encode('utf-8')


class SingleHTMLFormatter(object):
    def __init__(self, binder, archive_href=None):
        self.binder = binder
        self.archive_href = archive_href

        self.root = etree.fromstring(bytes(HTMLFormatter(self.binder)))

        self.head = self.xpath('//xhtml:head')[0]
        self.body = self.xpath('//xhtml:body')[0]

        self.built = False

    def xpath(self, path, elem=None):
        if elem is None:
            elem = self.root
        return elem.xpath(path, namespaces=HTML_DOCUMENT_NAMESPACES)

    def get_node_type(self, node):
        """If node is a document, the type is page.
        If node is a binder, the type is book.
        If node is a translucent binder, the type is either chapters (only
        contain pages) or unit (contains at least one translucent binder).
        """
        if isinstance(node, Document):
            return 'page'
        if isinstance(node, Binder):
            return 'book'
        for child in node:
            if isinstance(child, TranslucentBinder):
                return 'unit'
        return 'chapter'

    def _build_binder(self, binder, elem):
        for node in binder:
            child_elem = etree.SubElement(
                elem, 'div', **{'data-type': self.get_node_type(node)})
            if isinstance(node, TranslucentBinder):
                self._build_binder(node, child_elem)
            elif isinstance(node, Document):
                html = bytes(HTMLFormatter(node))
                doc_root = etree.fromstring(html)
                body = doc_root.xpath('//xhtml:body',
                                      namespaces=HTML_DOCUMENT_NAMESPACES)[0]
                for c in body.iterchildren():
                    child_elem.append(c)

    def build(self):
        self._build_binder(self.binder, self.body)

    def __unicode__(self):
        return self.__bytes__().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        if not self.built:
            self.build()
        return etree.tostring(self.root, pretty_print=True)


# XXX Rendering shouldn't happen here.
#     Temporarily place the rendering templates and code here.

DOCUMENT_POINTER_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:lrmi="http://lrmi.net/the-specification"
      >
  <head itemscope="itemscope"
        itemtype="http://schema.org/Book"
        >

    <title>{{ metadata['title']|escape }}</title>

    {# TODO Include this based on the feature being present #}
    <!-- These are for discoverability of accessible content. -->
    <meta itemprop="accessibilityFeature" content="MathML" />
    <meta itemprop="accessibilityFeature" content="LaTeX" />
    <meta itemprop="accessibilityFeature" content="alternativeText" />
    <meta itemprop="accessibilityFeature" content="captions" />
    <meta itemprop="accessibilityFeature" content="structuredNavigation" />

    {# TODO
       <meta refines="#<html-id>" property="display-seq" content="<ord>" />
     #}

  </head>
  <body xmlns:bib="http://bibtexml.sf.net/"
        xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
        itemscope="itemscope"
        itemtype="http://schema.org/Book"
        >
    <div data-type="metadata">
      <h1 data-type="document-title" itemprop="name">{{ \
              metadata['title']|escape }}</h1>
      <span data-type="document" data-value="pointer" />
      {% if metadata.get('cnx-archive-uri') %}
      <span data-type="cnx-archive-uri" data-value="{{ \
          metadata['cnx-archive-uri'] }}" />
      {%- endif %}
    </div>

    <div>
      <p>
        Click <a href="{{ metadata['url'] }}">here</a> to read {{ \
            metadata['title']|escape }}.
      </p>
    </div>
  </body>
</html>
"""
HTML_DOCUMENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:lrmi="http://lrmi.net/the-specification"
      >
  <head itemscope="itemscope"
        itemtype="http://schema.org/Book"
        >

    <title>{{ metadata['title']|escape }}</title>
    <meta itemprop="inLanguage"
          data-type="language"
          content="{{ metadata['language'] }}"
          />

    {# TODO Include this based on the feature being present #}
    <!-- These are for discoverability of accessible content. -->
    <meta itemprop="accessibilityFeature" content="MathML" />
    <meta itemprop="accessibilityFeature" content="LaTeX" />
    <meta itemprop="accessibilityFeature" content="alternativeText" />
    <meta itemprop="accessibilityFeature" content="captions" />
    <meta itemprop="accessibilityFeature" content="structuredNavigation" />

    {# TODO
       <meta refines="#<html-id>" property="display-seq" content="<ord>" />
     #}

    <meta itemprop="dateCreated"
          content="{{ metadata['created'] }}"
          />
    <meta itemprop="dateModified"
          content="{{ metadata['revised'] }}"
          />
  </head>
  <body xmlns:bib="http://bibtexml.sf.net/"
        xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
        itemscope="itemscope"
        itemtype="http://schema.org/Book"
        >
    <div data-type="metadata">
      <h1 data-type="document-title" itemprop="name">{{ \
              metadata['title']|escape }}</h1>
      {% if is_translucent %}
      <span data-type="binding" data-value="translucent" />
      {%- endif %}
      {% if metadata.get('cnx-archive-uri') %}
      <span data-type="cnx-archive-uri" data-value="{{ \
          metadata['cnx-archive-uri'] }}" />
      {%- endif %}

      <div class="authors">
        By:
        {% for author in metadata['authors'] -%}
          <span id="{{ '{}-{}'.format('author', loop.index) }}"
                itemscope="itemscope"
                itemtype="http://schema.org/Person"
                itemprop="author"
                data-type="author"
                >
            <a href="{{ author['id'] }}"
               itemprop="url"
               data-type="{{ author['type'] }}"
               >{{ author['name'] }}</a>
          </span>{% if not loop.last %}, {% endif %}
        {%- endfor %}

        Edited by:
        {% set person_type = 'editor' %}
        {% set person_itemprop_name = 'editor' %}
        {% set person_key = 'editors' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name'] }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

        Illustrated by:
        {% set person_type = 'illustrator' %}
        {% set person_itemprop_name = 'illustrator' %}
        {% set person_key = 'illustrators' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name'] }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

        Translated by:
        {% set person_type = 'translator' %}
        {% set person_itemprop_name = 'contributor' %}
        {% set person_key = 'translators' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name'] }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}

      </div>

      <div class="publishers">
        Published By:
        {% set person_type = 'publisher' %}
        {% set person_itemprop_name = 'publisher' %}
        {% set person_key = 'publishers' %}
        {% for person in metadata[person_key] -%}
          {% if isdict(person) %}
            <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                  itemscope="itemscope"
                  itemtype="http://schema.org/Person"
                  itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
                  >
              <a href="{{ person['id'] }}"
                 itemprop="url"
                 data-type="{{ person['type'] }}"
                 >{{ person['name'] }}</a>
            </span>{% if not loop.last %}, {% endif %}
          {% else %}
            <span itemprop="{{ person_type }}"
                  data-type="{{ person_type }}"
              >person</span>{% if not loop.last %}, {% endif %}
          {% endif %}
        {%- endfor %}
      </div>

      {% if metadata.get('derived_from_uri') %}
      <div class="derived-from">
        Derived from:
        <a href="{{ metadata['derived_from_uri'] }}"
           itemprop="isDerivedFromURL"
           data-type="derived-from"
           >{{ metadata['derived_from_title']|escape }}</a>
      </div>
      {%- endif %}

      {% if metadata.get('print_style') %}
      <div class="print-style">
        Print style:
        <span
           data-type="print-style"
           >{{ metadata['print_style'] }}</span>
      </div>
      {%- endif %}

      <div class="permissions">
        {% if metadata['copyright_holders'] %}
        <p class="copyright">
          Copyright:
          {% set person_type = 'copyright-holder' %}
          {% set person_itemprop_name = 'copyrightHolder' %}
          {% set person_key = 'copyright_holders' %}
          {% for person in metadata[person_key] -%}
            {% if isdict(person) %}
              <span id="{{ '{}-{}'.format(person_type, loop.index) }}"
                    itemscope="itemscope"
                    itemtype="http://schema.org/Person"
                    itemprop="{{ person_type }}"
                    data-type="{{ person_type }}"
                    >
                <a href="{{ person['id'] }}"
                   itemprop="url"
                   data-type="{{ person['type'] }}"
                   >{{ person['name'] }}</a>
              </span>{% if not loop.last %}, {% endif %}
            {% else %}
              <span itemprop="{{ person_type }}"
                    data-type="{{ person_type }}"
                >person</span>{% if not loop.last %}, {% endif %}
            {% endif %}
          {%- endfor %}
        </p>
        {% endif %}
        <p class="license">
          Licensed:
          <a href="{{ metadata['license_url'] }}"
             itemprop="dc:license,lrmi:useRightsURL"
             data-type="license"
             >{{ metadata['license_text'] }}</a>
        </p>
      </div>

      <div class="description"
           itemprop="description"
           data-type="description"
           >
        {{ metadata['summary'] }}
      </div>

      {% for keyword in metadata['keywords'] -%}
      <div itemprop="keywords" data-type="keyword">{{ keyword|escape }}</div>
      {%- endfor %}
      {% for subject in metadata['subjects'] -%}
      <div itemprop="about" data-type="subject">{{ subject|escape }}</div>
      {%- endfor %}

      {% if resources %}
      <div data-type="resources" style="display: none">
        <ul>
          {% for resource in resources -%}
          <li>{{ resource.id }}</li>
          {%- endfor %}
        </ul>
      </div>
      {%- endif %}

    </div>

   {{ content }}
  </body>
</html>
"""


# YANK This was pulled from cnx-archive to temporarily provide
#      a way to render the the tree to html. This either needs to
#      move elsewhere or preferably be replaced with a better solution.
def html_listify(tree, root_xl_element, extensions, list_type='ol'):
    for node in tree:
        li_elm = etree.SubElement(root_xl_element, 'li')
        if node['id'] == 'subcol':
            span_elm = etree.SubElement(li_elm, 'span')
            span_elm.text = node['title']
        else:
            a_elm = etree.SubElement(li_elm, 'a')
            a_elm.text = node['title']
            a_elm.set('href', ''.join([node['id'], extensions[node['id']]]))
        if 'contents' in node:
            elm = etree.SubElement(li_elm, list_type)
            html_listify(node['contents'], elm, extensions)


def tree_to_html(tree, extensions):
    nav = etree.Element('nav')
    nav.set('id', 'toc')
    ol = etree.SubElement(nav, 'ol')
    html_listify(tree['contents'], ol, extensions)
    return etree.tostring(nav)

# /YANK
