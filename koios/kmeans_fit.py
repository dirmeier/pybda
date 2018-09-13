# Copyright (C) 2018 Simon Dirmeier
#
# This file is part of koios.
#
# koios is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# koios is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with koios. If not, see <http://www.gnu.org/licenses/>.
#
# @author = 'Simon Dirmeier'
# @email = 'simon.dirmeier@bsse.ethz.ch'


import logging

from koios.io.as_filename import as_ssefile

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KMeansFit:
    def __init__(self, data, sse):
        self.__data = data
        self.__sse = sse

    @property
    def data(self):
        return self.__data

    @property
    def sse(self):
        return self.__sse

    def write_files(self, outfolder):
        self._write_sse(as_ssefile(outfolder))

    def _write_sse(self, outfile):
        logger.info("Writing SSE")
        with open(outfile, 'w') as fh:
            fh.write("SSE\n{}\n".format(self.__sse))
