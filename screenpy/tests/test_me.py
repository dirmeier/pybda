# screenpy: Analysis of big data perturbation screens.
#
# Copyright (C) Simon Dirmeier
#
# This file is part of screenpy.
#
# screenpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# screenpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with screenpy. If not, see <http://www.gnu.org/licenses/>.
#
#
# @author = 'Simon Dirmeier'
# @email = 'simon.dirmeier@bsse.ethz.ch'


import pytest
import unittest

class Test(unittest.TestCase):
    def setUp(self):
        self.a = 1

    def test_me(self):
        b = 1
        assert b == self.a
