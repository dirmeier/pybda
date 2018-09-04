#!/usr/bin/env python3

import argparse
import logging
import pathlib
import re
import sys
import glob
import pyspark
import pandas
import numpy
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from pyspark.ml.clustering import KMeansModel, KMeans
from pyspark.ml.feature import VectorAssembler
from pyspark.rdd import reduce
from pyspark.sql.functions import udf, col
from pyspark.sql.types import ArrayType, DoubleType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
frmtr = logging.Formatter(
  '[%(levelname)-1s/%(processName)-1s/%(name)-1s]: %(message)s')

spark = None


def read_args(args):
    parser = argparse.ArgumentParser(description='Cluster an RNAi dataset.')
    parser.add_argument('-o',
                        type=str,
                        help="the output folder the results are written to. "
                              "this is probablt a folder called 'kmeans-transformed'",
                        required=True,
                        metavar="output-folder")
    parser.add_argument('-f',
                        type=str,
                        help="the folder originally used for clustering. "
                             "this is probably a folder called 'outlier-removal' or so",
                        required=True,
                        metavar="input")
    parser.add_argument('-c',
                        type=str,
                        help="the folder prefix used for clustering. "
                             "this is probaly a folder called 'kmeans-fit'",
                        required=True,
                        metavar="input")
    opts = parser.parse_args(args)

    return opts.f, opts.o, opts.c, opts


def read_parquet_data(file_name):
    logger.info("Reading parquet: {}".format(file_name))
    return spark.read.parquet(file_name)


def write_parquet_data(file_name, data):
    logger.info("Writing parquet: {}".format(file_name))
    data.write.parquet(file_name, mode="overwrite")


def write_tsv_data(file_name, data):
    logger.info("Writing tsv: {}".format(file_name))
    data.write.csv(file_name, mode="overwrite", header=True, sep="\t")


def read_lrt_file(clusterprefix):
    logger.info("\tloading best clustering")
    mreg = clusterprefix + "-lrt_path.tsv"
    if not pathlib.Path(mreg).is_file():
        logger.error("Could not find LRT file!")
        raise ValueError("Could not find LRT file!")
    tab = pandas.read_csv(mreg, sep="\t")
    best_model = tab['current_model'].iloc[-1]
    fl = clusterprefix + "-K" + str(best_model)
    logger.info("\tbest model is: {}".format(best_model))
    return best_model, fl


def get_feature_columns(data):
    return list(filter(
      lambda x: any(x.startswith(f) for f in ["cells", "perin", "nucle"]),
      data.columns))


def get_optimal_k(outpath, clusterprefix):
    logger.info("Reading optimal K for transformation...")
    return read_lrt_file(clusterprefix)


def split_features(data):
    def to_array(col):
        def to_array_(v):
            return v.toArray().tolist()

        return udf(to_array_, ArrayType(DoubleType()))(col)

    logger.info("\tcomputing feature vectors")
    len_vec = len(data.select("features").take(1)[0][0])
    data = (data.withColumn("f", to_array(col("features")))
            .select(data.columns + [col("f")[i] for i in range(len_vec)])
            .drop("features"))

    for i, x in enumerate(data.columns):
        if x.startswith("f["):
            data = data.withColumnRenamed(
                x, x.replace("[", "_").replace("]", ""))

    return data


def write_clusters(data, outfolder, suff="", sort_me=True):

    outpath = outfolder + "-clusters" + str(suff)
    if not pathlib.Path(outpath).exists():
        pathlib.Path(outpath).mkdir()
    data = split_features(data)

    logger.info("Writing clusters to: {}".format(outpath))
    if sort_me:
        data.sort(col('prediction')).write.csv(
            path=outpath, sep='\t', mode='overwrite', header=True)
    else:
        data.write.csv(path=outpath, sep='\t', mode='overwrite', header=True)



def _select_desired_col(data):
    return data.select(
      "study", "pathogen", "library", "design", "replicate",
      "plate", "well", "gene", "sirna", "well_type",
      "image_idx", "object_idx", "prediction", "features")


def transform_cluster(datafolder, outpath, clusterprefix):
    data = read_parquet_data(datafolder)

    brst_model = get_optimal_k(outpath, clusterprefix)
    logger.info("Using model: {}".format(brst_model[0]))

    #model = KMeansModel.load(brst_model[1])

    # transform data and select
    #data_t = _select_desired_col(model.transform(data))
    #logger.info("Writing clustered data to parquet")

    #write_parquet_data(outpath, data)
    #write_clusters(data_t, outpath)
    # check if the assignment of clusters is stable or ust a waste of time
    check_cluster_stability(brst_model, data, outpath, clusterprefix, 5)


def check_cluster_stability(brst_model, data,
                            outpath, clusterprefix, stab_cnt):
    logger.info("Computing cluster stabilitiies")
    k = brst_model[0]
    for seed in range(stab_cnt):
        logger.info("Doing cluster with K={} and seed={}".format(k, seed))
        km = KMeans(k=k, seed=seed)
        model = km.fit(data)

        ccf = outpath + "-seed_{}".format(seed) + "_cluster_centers.tsv"
        logger.info("\tWriting cluster centers to: {}".format(ccf))
        with open(ccf, "w") as fh:
            fh.write("#Clustercenters\n")
            for center in model.clusterCenters():
                fh.write("\t".join(map(str, center)) + '\n')

        #data_t = _select_desired_col(model.transform(data))
        #write_clusters(data_t, outpath, suff="-seed_{}".format(seed), sort_me=False)
        logger.info("Writing stability computation number {}".format(seed))


def loggername(outpath):
    return outpath + ".log"


def run():
    # check files
    datafolder, outpath, clusterprefix, opts = read_args(sys.argv[1:])

    # logging format
    hdlr = logging.FileHandler(loggername(outpath))
    hdlr.setFormatter(frmtr)
    logger.addHandler(hdlr)

    if not pathlib.Path(datafolder).exists():
        logger.error("Please provide a file: " + datafolder)
        return

    logger.info("Starting Spark context")

    # spark settings
    pyspark.StorageLevel(True, True, False, False, 1)
    conf = pyspark.SparkConf()
    sc = pyspark.SparkContext(conf=conf)
    global spark
    spark = pyspark.sql.SparkSession(sc)

    try:
        transform_cluster(datafolder, outpath, clusterprefix)
    except Exception as e:
        logger.error("Some error: {}".format(str(e)))

    logger.info("Stopping Spark context")
    spark.stop()


if __name__ == "__main__":
    run()