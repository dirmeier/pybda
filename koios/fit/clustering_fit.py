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
import os
from abc import abstractmethod

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClusteringFit:
    def __init__(self, data, fit, n, p, k):
        self.__data = data
        self.__fit = fit
        self.__n = n
        self.__p = p
        self.__k = k

    def transform(self, data):
        return self.__fit.transform(data)

    @property
    def data(self):
        return self.__data

    @property
    def k(self):
        return self.__k

    @property
    def n(self):
        return self.__n

    @property
    def p(self):
        return self.__p

    @abstractmethod
    def write_files(self, outfolder):
        pass

    def as_statfile(self, fit_folder, k):
        return os.path.join(
          fit_folder, self._k_fit_path(k) + "_statistics.tsv")

    @abstractmethod
    def _k_fit_path(self, k):
        pass

    def _write_fit(self, outfolder):
        logger.info("Writing cluster fit to: {}".format(outfolder))
        self.__fit.write().overwrite().save(outfolder)

    def _write_cluster_sizes(self, outfile):
        comp_files = outfile + "_cluster_sizes.tsv"
        logger.info("Writing cluster size file to: {}".format(comp_files))
        with open(comp_files, 'w') as fh:
            for c in self.__fit.summary.clusterSizes:
                fh.write("{}\n".format(c))

    @abstractmethod
    def _write_statistics(self, outfile):
        pass

    @abstractmethod
    def load_model(self, statistics_file, load_fit=False):
        pass

    @classmethod
    def find_best_fit(cls, fit_folder):
        pass
