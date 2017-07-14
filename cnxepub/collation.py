# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import print_function
import io
import warnings

from lxml import etree
try:
    from cnxeasybake import Oven
except ImportError:
    warnings.warn("Missing the cnx-easybake package\n"
                  "HINT Make sure you install the 'collation' extra "
                  "requirements by doing something "
                  "like `pip install cnx-epub[collation]`.",
                  ImportWarning)
    raise

from .adapters import adapt_single_html
from .formatters import SingleHTMLFormatter


# XXX (1-Mar-2016) Not the final resting place.
def easybake(ruleset, in_html, out_html):
    """This adheres to the same interface as
    ``cnxeasybake.scripts.main.easyback``.
    ``ruleset`` is a string containing the ruleset CSS
    while ``in_html`` and ``out_html`` are file-like objects,
    with respective read and write ability.

    """
    html = etree.parse(in_html)
    oven = Oven(ruleset)
    oven.bake(html)
    out_html.write(etree.tostring(html))


def reconstitute(html):
    """Given a file-like object as ``html``, reconstruct it into models."""
    try:
        htree = etree.parse(html)
    except etree.XMLSyntaxError:
        html.seek(0)
        htree = etree.HTML(html.read())

    xhtml = etree.tostring(htree, encoding='utf-8')
    return adapt_single_html(xhtml)


def collate(binder, ruleset=None, includes=None):
    """Given a ``Binder`` as ``binder``, collate the content into a new set
    of models.
    Returns the collated binder.

    """
    html_formatter = SingleHTMLFormatter(binder, includes)
    raw_html = io.BytesIO(bytes(html_formatter))
    collated_html = io.BytesIO()

    if ruleset is None:
        # No ruleset found, so no cooking necessary.
        return binder

    easybake(ruleset, raw_html, collated_html)

    collated_html.seek(0)
    collated_binder = reconstitute(collated_html)

    return collated_binder


__all__ = (
    'collate',
    'reconstitute',
    )
