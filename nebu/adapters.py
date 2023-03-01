# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from __future__ import unicode_literals
import logging
import mimetypes

from nebu.models.base_binder import flatten_model, Binder, TranslucentBinder

logger = logging.getLogger('cnxepub')


__all__ = (
    'get_model_extensions',
    )


def get_model_extensions(binder):
    extensions = {}
    # Set model identifier file extensions.
    for model in flatten_model(binder):
        if isinstance(model, (Binder, TranslucentBinder,)):
            continue
        ext = mimetypes.guess_extension(model.media_type, strict=False)
        if ext is None:  # pragma: no cover
            raise ValueError("Can't apply an extension to media-type '{}'."
                             .format(model.media_type))
        extensions[model.id] = ext
        extensions[model.ident_hash] = ext
    return extensions
