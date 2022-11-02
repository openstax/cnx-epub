# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

from lxml import etree

from .adapters import adapt_single_html


def reconstitute(html):
    """Given a file-like object as ``html``, reconstruct it into models."""
    html.seek(0)
    htree = etree.parse(html)
    xhtml = etree.tostring(htree, encoding='utf-8')
    return adapt_single_html(xhtml)


__all__ = (
    'reconstitute',
    )
