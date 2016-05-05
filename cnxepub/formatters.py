# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import sys

import jinja2
from lxml import etree

from .models import (
    model_to_tree,
    Binder, TranslucentBinder,
    Document, DocumentPointer, CompositeDocument)
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
    def __init__(self, model, extensions=None):
        self.model = model
        self.extensions = extensions

    @property
    def _content(self):
        if isinstance(self.model, TranslucentBinder):
            if not self.extensions:
                from .adapters import get_model_extensions
                self.extensions = get_model_extensions(self.model)
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
    def __init__(self, binder):
        self.binder = binder

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
            child_elem = etree.SubElement(
                elem, 'div', **{'data-type': self.get_node_type(node)})
            if isinstance(node, TranslucentBinder):
                etree.SubElement(
                    child_elem, 'h1', **{'data-type': 'document-title'}
                    ).text = node.metadata['title']
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
        return etree.tostring(self.root, pretty_print=True, method='html')


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
