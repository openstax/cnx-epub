# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###

import os
import sys

# HTMLParser is deprecated in later versions
if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    import html
    parser = html
else: # pragma: no cover because who uses python 2 now? (FIXME: remove)
    try:
        import html.parser as HTMLParser
    except Exception:
        import HTMLParser
    parser = HTMLParser.HTMLParser()


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'tests', 'data')


def unescape(html):
    if isinstance(html, bytes):
        html = html.decode('utf-8')
    return parser.unescape(html)
