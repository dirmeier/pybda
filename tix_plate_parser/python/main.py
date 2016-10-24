# __author__ = 'Simon Dirmeier'
# __email__  = 'simon.dirmeier@bsse.ethz.ch'
# __date__   = 22/09/16

################################################################################
# Main file for plate_parser. Takes a folder of matlab files as input and
# converts every plate to a file in vsc format, where every line is ONE
# single cell.
#
# __author__ = 'Simon Dirmeier'
# __email__  = 'simon.dirmeier@bsse.ethz.ch'
# __date__   = 22/09/16
################################################################################

from __future__ import print_function, absolute_import

import argparse
import sys

from plate_parser.experiment_meta_files_loader import ExperimentMetaFileLoader
from plate_parser.plate_parser import PlateParser


def parse_options(args):
    parser = argparse.ArgumentParser(
        description='Parse matlab files of genetic perturbation screens.')
    parser.add_argument('-f',
                        type=str,
                        help='input folder, e.g. BRUCELLA-AU-CV3/VZ001-2H',
                        required=True,
                        metavar='input-folder')
    parser.add_argument('-m',
                        type=str,
                        help='tix layout meta file, e.g. '
                             'target_infect_x_library_layouts_beautified.tsv',
                        required=True,
                        metavar='layout-meta-file')
    parser.add_argument('-e',
                        type=str,
                        help='experiment meta file',
                        required=True,
                        metavar='experiment-meta-file')
    opts = parser.parse_args(args)
    return opts.f, opts.m, opts.e


def main(args):
    fold, meta, exm = parse_options(args)
    loader = ExperimentMetaFileLoader(exm, ".*/\w+\-[K|G][P|U]\-[G|K]\d+/.*")
    for f in loader:
        print(f)
    # create plate parser object and parse the single plates
    #parser = PlateParser(fold, meta)
    #parser.parse_plate_file_sets()


if __name__ == "__main__":
    main(sys.argv[1:])
