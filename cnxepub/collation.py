# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2016, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
import io

import cnxepub


# XXX (1-Mar-2016) Not the final resting place.
# from cnxeasybake.scripts.main import easybake
def easybake(ruleset, in_html, out_html):
    """This adheres to the same interface as
    ``cnxeasybake.scripts.main.easyback``.
    ``ruleset`` is a string containing the ruleset CSS
    while ``in_html`` and ``out_html`` are file-like objects,
    with respective read and write ability.

    """
    # TODO Add ``<span> pseudo cooked </span>`` to the head of each document
    # before writing.
    out_html.write(in_html.read())


def reconstitute(html):
    """Given a file-like object as ``html``, reconstruct it into models."""
    binder = None
    return binder


def collate(binder):
    """Given a ``Binder`` as ``binder``, collate the content into a new set
    of models.
    Returns the collated binder.

    """
    html_formatter = cnxepub.SingleHTMLFormatter(binder)
    raw_html = io.BytesIO(bytes(html_formatter))
    collated_html = io.BytesIO()

    # FIXME Seems like there should be a more definitive way
    # to get the ruleset file.
    try:
        ruleset_resource = [r for r in binder.resources
                            if r.filename == 'ruleset.css'][0]
    except IndexError:
        # No ruleset found, so no cooking necessary.
        return binder

    with ruleset_resource.open() as ruleset:
        easybake(ruleset.read(), raw_html, collated_html)

    collated_html.seek(0)
    collated_binder = reconstitute(collated_html)

    return collated_binder


__all__ = (
    'collate',
    'reconstitute',
    )
