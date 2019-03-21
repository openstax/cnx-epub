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
    leading_text = elm.text and elm.text or ''
    result = [leading_text]

    for child in elm.getchildren():
        # Encoding is set to utf-8 because otherwise `ó` would
        # become `&#243;`
        child_value = etree.tostring(child, encoding='utf-8')
        # Decode to a string for later regexp and whitespace stripping
        child_value = child_value.decode('utf-8')
        result.append(child_value)

    if remove_namespaces:
        # Best way to remove the namespaces without having the parser complain
        # about producing invalid XML.
        result = [re.sub(' xmlns:?[^=]*="[^"]*"', '', v) for v in result]

    # Join the results and strip any surrounding whitespace
    result = u''.join(result).strip()
    return result
