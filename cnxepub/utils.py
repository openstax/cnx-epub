# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2019, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
"""Various standalone utility functions that provide specific outcomes"""
import re

from lxml import etree


__all__ = (
    'squash_xml_to_text',
)


def squash_xml_to_text(elm, remove_namespaces=False):
    """Squash the given XML element (as `elm`) to a text containing XML.
    The outer most element/tag will be removed, but inner elements will
    remain. If `remove_namespaces` is specified, XML namespace declarations
    will be removed from the text.

    :param elm: XML element
    :type elm: :class:`xml.etree.ElementTree`
    :param remove_namespaces: flag to indicate the removal of XML namespaces
    :type remove_namespaces: bool
    :return: the inner text and elements of the given XML element
    :rtype: str

    """
    result = []
    if elm.text is not None:
        # Encode the text as XML entities (e.g. `ó` becomes `&#243;`)
        # This is done, because etree.tostring without utf-8 encoding
        # does this by default. We do the same to the text for consistency.
        text = elm.text.lstrip().encode('ascii', 'xmlcharrefreplace')
        result.append(text.decode('utf-8'))

    for child in elm.getchildren():
        # Encoding is not set to utf-8 because otherwise `ó` wouldn't
        # become `&#243;`
        child_value = etree.tostring(child)
        # Decode to a string and strip the whitespace
        child_value = child_value.decode('utf-8')
        result.append(child_value)

    if remove_namespaces:
        # Best way to remove the namespaces without having the parser complain
        # about producing invalid XML.
        result = [re.sub(' xmlns:?[^=]*="[^"]*"', '', v) for v in result]

    # Join the results and strip any surrounding whitespace
    result = ''.join(result).strip()
    return result
