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

import click
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.regression import RandomForestRegressor

from koios.fit.forest_fit import ForestFit
from koios.globals import GAUSSIAN_, BINOMIAL_
from koios.regression import Regression

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Forest(Regression):
    def __init__(self, spark, response, meta, features, family=GAUSSIAN_,
                 n_trees=50, max_depth=10, subsampling_rate=0.5):
        super().__init__(spark, family, response, features)
        self.__n_trees = n_trees
        self.__max_depth = max_depth
        self.__subsampling_rate = subsampling_rate
        self.__meta = meta

    def fit(self, data):
        logger.info("Fitting forest with family='{}'".format(self.family))
        model = self._fit(data)
        data = model.transform(data)
        return ForestFit(data, model, self.response,
                         self.family, self.features)

    def _model(self):
        if self.family == GAUSSIAN_:
            reg = RandomForestRegressor
        elif self.family == BINOMIAL_:
            reg = RandomForestClassifier
        else:
            raise NotImplementedError(
              "Family '{}' not implemented".format(self.family))
        model = reg(subsamplingRate=self.__subsampling_rate, seed=23,
                    numTrees=self.__n_trees, maxDepth=self.__max_depth)
        logger.info(self.response)
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
    from koios.util.string import drop_suffix
    from koios.logger import set_logger
    from koios.spark_session import SparkSession
    from koios.io.as_filename import as_logfile
    from koios.io.io import read_and_transmute, read_column_info

    outpath = drop_suffix(outpath, "/")
    set_logger(as_logfile(outpath))

    with SparkSession() as spark:
        try:
            meta, features = read_column_info(meta, features)
            data = read_and_transmute(spark, file, features, response)
            fl = Forest(spark, response, meta, features, family)
            logger.info("sadasdasasdasd")
            fit = fl.fit(data)
            logger.info("sadasdasd")
            fit.write_files(outpath)
            if pathlib.Path(predict).exists():
                logger.info("sadasdasd2")
                pre_data = read_and_transmute(
                  spark, predict, features, drop=False)
                pre_data = fit.transform(pre_data)
                pre_data.write_files(outpath)

        except Exception as e:
            logger.error("Some error: {}".format(str(e)))


if __name__ == "__main__":
    run()
