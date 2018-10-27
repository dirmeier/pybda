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
import pathlib

import pandas

from koios.globals import TSV_
from koios.util.features import to_double, fill_na, assemble
from koios.util.string import matches

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def parquet_data_path(file_name):
    """
    Takes a file name with '.tsv' suffix and converts into a 'parquet' file
    name

    :param file_name: the file name from which the parquet name is computed
    :return: string of parquet file name
    """

    return file_name.replace(".tsv", "_parquet")


def write_parquet(data, outfolder):
    """
    Write a data frama to an outpath in parquet format.
    Overwrites existing files!

    :param data: data frame
    :param outfolder: the path where the dataframe is written to
    """

    logger.info("Writing parquet: {}".format(outfolder))
    data.write.parquet(outfolder, mode="overwrite")


def write_tsv(data, outfile, header=True, index=True):
    """
    Write a data frama to an outpath as tsv file.
    Overwrites existing files!

    :param data: data frame
    :param outfile: the path where the dataframe is written to
    """

    import pandas
    logger.info("Writing tsv: {}".format(outfile))
    if isinstance(data, pandas.DataFrame):
        data.to_csv(outfile, sep="\t", header=header, index=index)
    else:
        data.write.csv(outfile, mode="overwrite", sep="\t", header=True)


def read_and_transmute(spark, file_name,
                       feature_cols,
                       respone=None,
                       header=True,
                       drop=True):
    """
    Reads either a 'tsv' or 'parquet' file as data frame.

    :param spark: a running spark session
    :type spark: pyspark.sql.SparkSession
    :param file_name: the name of the tsv or parquet file as string
    :param feature_cols: a comma separated li
    :param respone: the column name of the response if any
    :param header: boolean if the tsv has a header
    :param drop: boolean if feature columns should get dropped after assembly
    :return: returns a tuple (DataFrame, list(str)) where the second element is
        a list of features
    """

    if file_name.endswith(TSV_):
        data = read_tsv(spark, file_name, header)
    elif matches(file_name, ".*/.+\..+"):
        raise ValueError("Can only parse tsv files or parquet folders.")
    elif pathlib.Path(file_name).is_dir():
        data = read_parquet(spark, file_name, header)
    else:
        raise ValueError("{} is neither tsv nor folder.".format(file_name))
    data = to_double(data, feature_cols, respone)
    data = fill_na(data)
    data = assemble(data, feature_cols, drop)

    return data


def read_tsv(spark, file_name, header='true'):
    """
    Reads a tsv file as data frame

    :param spark: a running spark session
    :type spark: pyspark.sql.SparkSession
    :param file_name: the name of the tsv as string
    :param header: boolean if the tsv has a header
    :return: returns a data frame
    """

    logger.info("Reading tsv: {}".format(file_name))
    return spark.read.csv(path=file_name, sep="\t", header=header)


def read_parquet(spark, folder_name):
    """
    Reads a data frame from a parquet folder.

    :param spark: a running sparksession
    :type spark: pyspark.sql.SparkSession
    :param folder_name: the parquet folder to read
    :return: returns a data frame
    """

    logger.info("Reading parquet folder: {}".format(folder_name))
    return spark.read.parquet(folder_name)


def write_line(string, outfile):
    with open(outfile, 'w') as fh:
        fh.write(string)


def mkdir(path):
    if not pathlib.Path(path).exists():
        pathlib.Path(path).mkdir()
        return True
    return False


def rm(files):
    for file in files:
        pathlib.Path(file).unlink()


def read_column_info(meta, features):
    meta = list((pandas.read_csv(meta, header=None))[0].values)
    features = list((pandas.read_csv(features, header=None))[0].values)
    return meta, features
