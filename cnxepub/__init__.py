# -*- coding: utf-8 -*-
# ###
# Copyright (c) 2013, Rice University
# This software is subject to the provisions of the GNU Affero General
# Public License version 3 (AGPLv3).
# See LICENCE.txt for details.
# ###
from .epub import *
from .formatters import *
from .models import *
from .adapters import *

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
