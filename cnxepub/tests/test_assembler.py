import os
from pathlib import Path

import unittest
from ..testing import TEST_DATA_DIR

from cnxepub.pipeline import assemble_collection_html


class AssembleSingleHTMLTestCase(unittest.TestCase):
    def setUp(self):
        # self.source_dir = os.path.join(TEST_DATA_DIR, 'col11562_1.23_complete')
        pass

    def test_create_a_single_collection_html(self):
        # generate module HTML files

        # create some kind of struct or object to store the module HTML files
        # ... along with their resources – as well as the collection.xml

        # assert that the content from each of the modules exists in the output

        # assert that the ``nav`` in the output HTML files matches the
        # ... structure of the collection.xml file
        pass

    def test_parse_into_a_tree(self):
        assemble_collection_html()

        # from pathlib import Path
        # with Path(self.source_dir).open('rb') as f:
        #     assemble_collection_html(f.read())
