# Copyright (C) 2018 Simon Dirmeier
#
# This file is part of pybda.
#
# pybda is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pybda is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pybda. If not, see <http://www.gnu.org/licenses/>.
#
# @author = 'Simon Dirmeier'
# @email = 'simon.dirmeier@bsse.ethz.ch'

import logging

import click
from pyspark.ml.classification import GBTClassifier
from pyspark.ml.regression import GBTRegressor

from pybda.ensemble import Ensemble
from pybda.globals import GAUSSIAN_, BINOMIAL_

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class GBM(Ensemble):
    def __init__(self, spark, response, meta, features, family=GAUSSIAN_,
                 max_iter=25, step_size=0.1, max_depth=10,
                 subsampling_rate=0.5):
        super().__init__(spark, family, response, features, max_depth,
                         subsampling_rate)
        self.__meta = meta
        self.__max_iter = max_iter
        self.__step_size = step_size

    def _model(self):
        if self.family == GAUSSIAN_:
            reg = GBTRegressor
        elif self.family == BINOMIAL_:
            reg = GBTClassifier
        else:
            raise NotImplementedError("Family '{}' not implemented".format(
                self.family))
        model = reg(subsamplingRate=self.subsampling_rate, seed=23,
                    stepSize=self.__step_size, maxDepth=self.max_depth,
                    maxIter=self.__max_iter)
        model.setLabelCol(self.response)
        return model

    def fit_transform(self):
        raise NotImplementedError()

    def transform(self, predict):
        raise NotImplementedError()


@click.command()
@click.argument("file", type=str)
@click.argument("meta", type=str)
@click.argument("features", type=str)
@click.argument("response", type=str)
@click.argument("family", type=str)
@click.argument("outpath", type=str)
@click.option("-p", "--predict", default="None")
def run(file, meta, features, response, family, outpath, predict):
    """
    Fit a generalized linear regression model.
    """

    import pathlib
    from pybda.util.string import drop_suffix
    from pybda.logger import set_logger
    from pybda.spark_session import SparkSession
    from pybda.io.as_filename import as_logfile
    from pybda.io.io import read_and_transmute, read_column_info

    outpath = drop_suffix(outpath, "/")
    set_logger(as_logfile(outpath))

    with SparkSession() as spark:
        try:
            meta, features = read_column_info(meta, features)
            data = read_and_transmute(spark, file, features, response)
            fl = GBM(spark, response, meta, features, family)
            fit = fl.fit(data)
            fit.write_files(outpath)
            if pathlib.Path(predict).exists():
                pre_data = read_and_transmute(spark, predict, features,
                                              drop=False)
                pre_data = fit.transform(pre_data)
                pre_data.write_files(outpath)

        except Exception as e:
            logger.error("Some error: {}".format(str(e)))


if __name__ == "__main__":
    run()
