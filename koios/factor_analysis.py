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
import numpy
import pyspark

import pyspark.sql.functions as func
from pyspark.ml.linalg import VectorUDT
from pyspark.mllib.linalg.distributed import RowMatrix, DenseMatrix
from pyspark.sql.functions import udf

from koios.dimension_reduction import DimensionReduction
from koios.factor_analysis_fit import FactorAnalysisFit
from koios.io.io import read_tsv
from koios.util.features import feature_columns, to_double, fill_na
from koios.util.stats import svd, column_statistics


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FactorAnalysis(DimensionReduction):

    def __init__(self, spark, threshold=1e-9, max_iter=100):
        super().__init__(spark, threshold, max_iter)

    @staticmethod
    def _tilde(X, psi_sqrt, n_sqrt):
        norm = psi_sqrt * n_sqrt
        return RowMatrix(X.rows.map(lambda x: x / norm))

    @staticmethod
    def _loglik(llconst, unexp_var, s, psi, n):
        ll = llconst + numpy.sum(numpy.log(s))
        ll += unexp_var + numpy.sum(numpy.log(psi))
        ll *= -n / 2.

        return ll

    @staticmethod
    def _update_factors(s, V, sqrt_psi):
        W = numpy.sqrt(numpy.maximum(s - 1., 0.))[:, numpy.newaxis] * V
        W *= sqrt_psi
        return W

    def _update_variance(self, var, W):
        psi = numpy.maximum(var - numpy.sum(W ** 2, axis=0), self.threshold)
        return psi

    def _estimate(self, X, var, n_factors):
        n, p = X.numRows(), X.numCols()
        old_ll = -numpy.inf
        llconst = p * numpy.log(2. * numpy.pi) + n_factors
        psi = numpy.ones(p, dtype=numpy.float32)
        nsqrt = numpy.sqrt(n)
        logliks = []

        logger.info("Computing factor analysis")
        for i in range(self.max_iter):
            sqrt_psi = numpy.sqrt(psi) + self.threshold
            s, V, unexp_var = svd(self._tilde(X, sqrt_psi, nsqrt), n_factors)
            s = s ** 2

            # factor updated
            W = self._update_factors(s, V, sqrt_psi)
            # loglik update
            ll = self._loglik(llconst, unexp_var, s, psi, n)
            logliks.append(ll)
            # variance update
            psi = self._update_variance(var, W)

            if abs(ll - old_ll) < 0.001:
                break
            old_ll = ll

        return W, logliks, psi

    def _transform(self, X, W, psi):
        logger.info("Transforming data")
        Ih = numpy.eye(len(W))
        Wpsi = W / psi
        cov_z = numpy.linalg.inv(Ih + numpy.dot(Wpsi, W.T))
        tmp = numpy.dot(Wpsi.T, cov_z)
        tmp_dense = DenseMatrix(
          numRows=tmp.shape[0], numCols=tmp.shape[1], values=tmp.flatten())

        as_ml = udf(lambda v: v.asML() if v is not None else None, VectorUDT())

        X = X.multiply(tmp_dense)
        X = self.spark.createDataFrame(X.rows.map(lambda x: (x,)))
        X = X.withColumnRenamed("_1", "features")
        X = X.withColumn("features", as_ml("features"))

        return X

    def fit(self, data, n_factors):
        logger.info("Running factor analysis ...")
        X = data.select(feature_columns(data)).rdd.map(numpy.array)
        means, var = column_statistics(X)
        X = RowMatrix(X.map(lambda x: x - means))
        W, ll, psi = self._estimate(X, var, n_factors)
        X = self._transform(X, W, psi)

        data = self._join(data, X)
        del X

        return FactorAnalysisFit(data, W, psi, ll)

    @staticmethod
    def _join(data, X):
        X = X.withColumn("row_index", func.monotonically_increasing_id())
        data = data.withColumn("row_index", func.monotonically_increasing_id())
        data = data.join(
          X["row_index", "features"], on=["row_index"]).drop("row_index")

        return data


@click.command()
@click.argument("factors", type=int)
@click.argument("file", type=str)
@click.argument("outpath", type=str)
def run(factors, file, outpath):
    if outpath.endswith("/"):
        outpath = outpath[:-1]
    hdlr = logging.FileHandler(outpath + ".log")
    hdlr.setFormatter(
      logging.Formatter(
        '[%(asctime)s - %(levelname)s - %(name)s]: %(message)s')
    )
    root_logger = logging.getLogger()
    root_logger.addHandler(hdlr)

    logger.info("Initializing pyspark session")
    pyspark.StorageLevel(True, True, False, False, 1)
    spark = pyspark.sql.SparkSession.builder.getOrCreate()
    for conf in spark.sparkContext.getConf().getAll():
        logger.info("Config: {}, value: {}".format(conf[0], conf[1]))

    try:
        data = read_tsv(spark, file)
        data = to_double(data, feature_columns(data))
        data = fill_na(data)
        fl = FactorAnalysis(spark, max_iter=25)
        fit = fl.fit(data, factors)
        fit.write_files(outpath)
    except Exception as e:
        logger.error("Some error: {}".format(str(e)))

    logger.info("Stopping pyspark context")
    spark.stop()


if __name__ == "__main__":
    run()