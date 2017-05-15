# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from contextlib import contextmanager
try:
    import html.parser as HTMLParser
except:
    import HTMLParser
from io import StringIO
import memcache
import os
import tempfile
import shutil
import sys
import unittest
import zipfile


here = os.path.abspath(os.path.dirname(__file__))
TEST_DATA_DIR = os.path.join(here, 'tests', 'data')


class EPUBTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def pack_epub(self, directory):
        """Given an directory containing epub contents,
        pack it up and make return filepath.
        Packed file is remove on test exit.
        """
        zip_fd, zip_filepath = tempfile.mkstemp('.epub', dir=self.tmpdir)
        with zipfile.ZipFile(zip_filepath, 'w') as zippy:
            base_path = os.path.abspath(directory)
            for root, dirs, filenames in os.walk(directory):
                # Strip the absolute path
                archive_path = os.path.abspath(root)[len(base_path):]
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    archival_filepath = os.path.join(archive_path, filename)
                    zippy.write(filepath, archival_filepath)
        return zip_filepath

    def copy(self, src, dst_name='book'):
        """Convenient method for copying test data directories."""
        dst = os.path.join(self.tmpdir, dst_name)
        shutil.copytree(src, dst)
        return dst


# noqa from http://stackoverflow.com/questions/4219717/how-to-assert-output-with-nosetest-unittest-in-python
@contextmanager
def captured_output():
    if sys.version_info[0] == 3:
        new_out, new_err = StringIO(), StringIO()
    else:
        from io import BytesIO
        new_out, new_err = BytesIO(), BytesIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def unescape(html):
    p = HTMLParser.HTMLParser()
    if isinstance(html, bytes):
        html = html.decode('utf-8')
    return p.unescape(html)


def is_memcache_enabled():
    mc = _get_memcache_client()
    is_enabled = bool(mc.get_stats())
    return is_enabled


def _get_memcache_client():
    memcache_servers = ['127.0.0.1:11211']
    mc = memcache.Client(memcache_servers, debug=0)
    return mc

IS_MEMCACHE_ENABLED = is_memcache_enabled()
