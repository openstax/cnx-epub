# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import random
import sys

import re
import jinja2
import lxml.html
from lxml import etree
from copy import deepcopy

from .models import (
    model_to_tree,
    flatten_to_documents,
    Binder, TranslucentBinder,
    Document, DocumentPointer, CompositeDocument, utf8)
from .html_parsers import HTML_DOCUMENT_NAMESPACES


IS_PY3 = sys.version_info.major == 3


__all__ = (
    'DocumentContentFormatter',
    'DocumentSummaryFormatter',
    'HTMLFormatter',
    'SingleHTMLFormatter',
    )


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


class DocumentSummaryFormatter(object):
    def __init__(self, document):
        self.document = document

    def __unicode__(self):
        return self.__bytes__().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        # try to make sure summary is wrapped in a tag
        summary = self.document.metadata['summary']
        try:
            etree.fromstring(summary)
            html = '{}'.format(summary)
        except etree.XMLSyntaxError:
            html = """\
<div class="description" data-type="description"\
 xmlns="http://www.w3.org/1999/xhtml">
  {}
</div>""".format(summary)
        return html.encode('utf-8')


class HTMLFormatter(object):
    def __init__(self, model, extensions=None, generate_ids=False):
        self.model = model
        self.extensions = extensions
        self.generate_ids = generate_ids

    def _generate_ids(self, document, content):
        """Generate unique ids for html elements in page content so that it's
        possible to link to them.
        """
        existing_ids = content.xpath('//*/@id')
        elements = [
            'p', 'dl', 'dt', 'dd', 'table', 'div', 'section', 'figure',
            'blockquote', 'q', 'code', 'pre', 'object', 'img', 'audio',
            'video',
            ]
        elements_xpath = '|'.join(['.//{}|.//xhtml:{}'.format(elem, elem)
                                  for elem in elements])

        data_types = [
            'equation', 'list', 'exercise', 'rule', 'example', 'note',
            'footnote-number', 'footnote-ref', 'problem', 'solution', 'media',
            'proof', 'statement', 'commentary'
            ]
        data_types_xpath = '|'.join(['.//*[@data-type="{}"]'.format(data_type)
                                     for data_type in data_types])

        xpath = '|'.join([elements_xpath, data_types_xpath])

        mapping = {}  # old id -> new id

        for node in content.xpath(xpath, namespaces=HTML_DOCUMENT_NAMESPACES):
            old_id = node.attrib.get('id')
            document_id = document.id.replace('_', '')
            if old_id:
                new_id = 'auto_{}_{}'.format(document_id, old_id)
            else:
                random_number = random.randint(0, 100000)
                new_id = 'auto_{}_{}'.format(document_id, random_number)
            while new_id in existing_ids:
                random_number = random.randint(0, 100000)
                new_id = 'auto_{}_{}'.format(document_id, random_number,
                                             random_number)
            node.attrib['id'] = new_id
            if old_id:
                mapping[old_id] = new_id
            existing_ids.append(new_id)

        for a in content.xpath('//a[@href]|//xhtml:a[@href]',
                               namespaces=HTML_DOCUMENT_NAMESPACES):
            href = a.attrib['href']
            if href.startswith('#') and href[1:] in mapping:
                a.attrib['href'] = '#{}'.format(mapping[href[1:]])

    @property
    def _content(self):
        if isinstance(self.model, TranslucentBinder):
            if not self.extensions:
                from .adapters import get_model_extensions
                self.extensions = get_model_extensions(self.model)
            return tree_to_html(
                model_to_tree(self.model), self.extensions).decode('utf-8')
        elif isinstance(self.model, Document):
            content = self.model.content
            if self.generate_ids:
                _html = deepcopy(self.model._xml)
                self._generate_ids(self.model, _html)
                content = ''.join(utf8([
                                   isinstance(node, (type(''), type(b''))) and
                                   node or etree.tostring(node)
                                   for node in _html.xpath('node()')]))
            return content

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
        if isinstance(self.model, Document):
            root = self.model._xml
        else:
            root = {}
        return {
            'metadata': self.model.metadata,
            'content': self._content,
            'is_translucent': getattr(self.model, 'is_translucent', False),
            'resources': getattr(self.model, 'resources', []),
            'root_attrs': {k: root.get(k) for k in root.keys()}
            }

    def __unicode__(self):
        return self.__bytes().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        html = self._template.render(self._template_args)
        return _fix_namespaces(html.encode('utf-8'))


class SingleHTMLFormatter(object):
    def __init__(self, binder, includes=None):
        self.binder = binder

        self.root = etree.fromstring(bytes(HTMLFormatter(self.binder)))

        self.head = self.xpath('//xhtml:head')[0]
        self.body = self.xpath('//xhtml:body')[0]

        self.built = False
        self.includes = includes

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
        if isinstance(node, CompositeDocument):
            return 'composite-page'
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
            attrs = {'data-type': self.get_node_type(node)}
            if node.id:
                attrs['id'] = node.id
            child_elem = etree.SubElement(elem, 'div', **attrs)
            if isinstance(node, TranslucentBinder):
                etree.SubElement(
                    child_elem, 'h1', **{'data-type': 'document-title'}
                    ).text = node.metadata['title']
                self._build_binder(node, child_elem)
            elif isinstance(node, Document):
                html = bytes(HTMLFormatter(node, generate_ids=True))
                doc_root = etree.fromstring(html)
                body = doc_root.xpath('//xhtml:body',
                                      namespaces=HTML_DOCUMENT_NAMESPACES)[0]
                for c in body.iterchildren():
                    child_elem.append(c)
                for a in body.attrib:
                    if not (a.startswith('item')):
                        child_elem.set(a, body.get(a))

    def build(self):
        self._build_binder(self.binder, self.body)
        # Fetch any includes from remote sources
        if self.includes is not None:
            for match, proc in self.includes:
                for elem in self.xpath(match):
                    proc(elem)

        # Rewrite absolute-path links that are intra-binder
        page_ids = [page.id for page in flatten_to_documents(self.binder)]
        page_uuids = {id.split('@')[0]: id for id in page_ids}
        for link in self.root.xpath('//*[@href]'):
            href = link.get('href')
            if href.startswith('/contents/'):
                link_uuid = re.split('@|#', href[10:])[0]
                if link_uuid in page_uuids:
                    if '#' in href:
                        fragment = href[href.index('#'):].replace('#', '_')
                        link.set('href', '#auto_{}{}'.format(
                            page_uuids[link_uuid], fragment))
                    else:
                        link.set('href', '#{}'.format(page_uuids[link_uuid]))

    def __unicode__(self):
        return self.__bytes__().decode('utf-8')

    def __str__(self):
        if IS_PY3:
            return self.__bytes__().decode('utf-8')
        return self.__bytes__()

    def __bytes__(self):
        if not self.built:
            self.build()
        return _fix_namespaces(etree.tostring(self.root,
                                              pretty_print=True,
                                              method='html',
                                              encoding='utf-8'))


def _fix_namespaces(html):
    nsmap = {u"": u"http://www.w3.org/1999/xhtml",
             u"m": u"http://www.w3.org/1998/Math/MathML",
             u"epub": u"http://www.idpf.org/2007/ops",
             u"rdf": u"http://www.w3.org/1999/02/22-rdf-syntax-ns#",
             u"dc": u"http://purl.org/dc/elements/1.1/",
             u"lrmi": u"http://lrmi.net/the-specification",
             u"bib": u"http://bibtexml.sf.net/",
             u"data":
                 u"http://www.w3.org/TR/html5/dom.html#custom-data-attribute",
             u"qml": u"http://cnx.rice.edu/qml/1.0",
             u"datadev": u"http://dev.w3.org/html5/spec/#custom",
             u"mod": u"http://cnx.rice.edu/#moduleIds",
             u"md": u"http://cnx.rice.edu/mdml",
             u"c": u"http://cnx.rice.edu/cnxml"
             }
    from xml.etree import ElementTree as ET
    from io import BytesIO
    for prefix, uri in nsmap.items():
        ET.register_namespace(prefix, uri)
    et = ET.parse(BytesIO(html))
    new_html = BytesIO()
    et.write(new_html)
    new_html.seek(0)
    let = etree.parse(new_html)
    return etree.tostring(let, pretty_print=True,
                          method='html', encoding='utf-8')


# XXX Rendering shouldn't happen here.
#     Temporarily place the rendering templates and code here.

DOCUMENT_POINTER_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:lrmi="http://lrmi.net/the-specification"
      xmlns:bib="http://bibtexml.sf.net/"
      xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
      xmlns:qml="http://cnx.rice.edu/qml/1.0"
      xmlns:datadev="http://dev.w3.org/html5/spec/#custom"
      xmlns:mod="http://cnx.rice.edu/#moduleIds"
      xmlns:md="http://cnx.rice.edu/mdml"
      xmlns:c="http://cnx.rice.edu/cnxml"
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
  <body itemscope="itemscope"
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
      xmlns:bib="http://bibtexml.sf.net/"
      xmlns:data="http://www.w3.org/TR/html5/dom.html#custom-data-attribute"
      xmlns:qml="http://cnx.rice.edu/qml/1.0"
      xmlns:datadev="http://dev.w3.org/html5/spec/#custom"
      xmlns:mod="http://cnx.rice.edu/#moduleIds"
      xmlns:md="http://cnx.rice.edu/mdml"
      xmlns:c="http://cnx.rice.edu/cnxml"
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
  <body itemscope="itemscope"
        itemtype="http://schema.org/Book"
      {% for attr,value in root_attrs.items() %}
        {{ attr }}="{{ value }}"
      {%- endfor %}
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

      {% if metadata['summary'] %}
      <div class="description"
           itemprop="description"
           data-type="description"
           >
        {{ metadata['summary'] }}
      </div>
      {%- endif %}


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
          <li><a href="{{ resource.id }}">{{ resource.filename }}</a></li>
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
            span_elm = lxml.html.fragment_fromstring(
                node['title'], create_parent='span')
            li_elm.append(span_elm)
        else:
            a_elm = lxml.html.fragment_fromstring(
                node['title'], create_parent='a')
            a_elm.set('href', ''.join([node['id'], extensions[node['id']]]))
            li_elm.append(a_elm)
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
