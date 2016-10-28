# __author__ = 'Simon Dirmeier'
# __email__  = 'simon.dirmeier@bsse.ethz.ch'
# __date__   = 22/09/16

import logging
import numpy
import multiprocessing as mp

from ._plate_sirna_gene_mapping import PlateSirnaGeneMapping
from ._utility import load_matlab
from .plate_loader import PlateLoader
from ._plate_cell_features import PlateCellFeature
from .plate_file_set_parser import PlateFileSetParser

logger = mp.log_to_stderr()
logger.setLevel(logging.INFO)


class PlateParser:
    """
    Class for parsing a folder of plates containing matlab files for the
    features.

    """

    # meta information header for a single cell
    _meta = ["pathogen", "library_vendor", "library_type", "screen",
             "replicate",
             "plate", "sirna", "gene",
             "well", "welltype", "image", "cell_number"]

    def __init__(self, experiment_meta, layout_meta,
                 bee_loader, output_path, username, pw):
        """
        Constructor for PlateParser.

        :param experiment_meta: parsed experiment meta files
        :param layout_meta: parsed layout meta
        :param bee_loader: the full path with the script name that downloads
         the data (e.g. /bla/..../BeeDataSetDownloader.sh)
        :param output_path: the folder where all the plates get stored and
        parsed to
        :param username: the user name of the open bis instance
        :param pw: the password of the open bis instance
        """

        # parse the folder into a map of (classifier-plate) pairs
        self._experiment_meta = experiment_meta
        self._layout_meta = layout_meta
        self._bee_loader = bee_loader
        self._username = username
        self._pw = pw
        self._output_path = output_path
        self._downloader = PlateLoader(bee_loader, output_path, username, pw)

    def parse(self):
        """
        Iterate over the experiments, download the files, parse them and
        store to tsv.

        """
        lock = mp.Lock()
        cnt = 0
        logger.info("Going parallel...")
        for plate in self._experiment_meta:
            cnt += 1
            if cnt == 10:
                break
            mp.Process(target=self._parse, args=(lock, plate)).start()

    def _parse(self, lock, plate):
        # plate file name
        pa = self._output_path + "/" + plate
        # download the plate files with a process lock
        self._downloader.load(plate, lock)
        # parse the plate file names
        platefilesets = PlateFileSetParser(pa, self._output_path)
        if len(platefilesets) > 1:
            logger.warn("Found multiple plate identifiers for: " + plate)
        # parse the files
        self._parse_plate_file_sets(platefilesets)
        # remove the matlab plate files
        # TODO
        #platefilesets.remove()

    def _parse_plate_file_sets(self, platefilesets):
        """
        Parse the PlateFileSets (i.e.: all parsed folders) into tsvs.

        Iterate over the file sets and create matrices every platefileset
        represents a plate so every platefileset is a single file

        """

        for platefileset in platefilesets:
            # parse the feates to np arrays
            features = self._parse_plate_file_set(platefileset)
            # load the mapping file for the wells
            mapping = self._parse_plate_mapping(platefileset)
            self._integrate_platefileset(platefileset, features, mapping)

    def _parse_plate_file_set(self, plate_file_set):
        features = {}
        logger.info("Doing: " + str(plate_file_set.classifier))
        for plate_file in plate_file_set:
            cf = self._parse_file(plate_file)
            if cf is None:
                continue
            self._add(features, cf)
        return features

    def _parse_file(self, plate_file):
        """
        Parse a matlab binary as np.array

        :param plate_file: the matlab file
        :return: returns a 2D np.array
        """
        featurename = plate_file.featurename
        file = plate_file.filename
        matrix = None
        try:
            matrix = \
                self._alloc(
                    load_matlab(file),
                    file, featurename)
        except ValueError or TypeError or AssertionError:
            logger.warn("Could not parse: %s", file)
        return matrix

    def _alloc(self, arr, file, featurename):
        """
        Create a Cell feature object from a matlab binary.

        :param arr: the matrix object
        :param file: the filename of the matlab binary
        :param featurename: the name of the feature
        :return: return a plate cell feature
        """
        featurename = str(featurename).replace(".mat", "")
        try:
            # number of images on the plate (usually 9 * 384)
            nrow = len(arr)
            # number of cells per image
            rowlens = [len(x) for x in arr]
            # maximum number of cells
            m_ncol = max(rowlens)
            # initialize empty matrix of NaNs
            mat = numpy.full(shape=(nrow, m_ncol), fill_value=numpy.nan,
                             dtype="float64")
            # fill matrix
            for i in range(len(arr)):
                row = arr[i]
                for j in range(len(row)):
                    mat[i][j] = row[j]
            return PlateCellFeature(mat, nrow, m_ncol, file, rowlens,
                                    featurename)
        except AssertionError:
            logger.warn("Could not alloc feature %s of %s", featurename, file)
        return None

    def _add(self, features, cf):
        """
        Add a cell feature to a feature map

        :param features: the feature map
        :param cf: the cell feature object
        """
        # TODO: is this really enough?
        # maybe compare all cell numbers and not only the max cell number
        max_cells = str(cf.max_cells)
        if max_cells not in features:
            features[max_cells] = []
        features[max_cells].append(cf)

    def _parse_plate_mapping(self, plate_file_set):
        logger.info("#Loading meta: " + str(plate_file_set.classifier))
        mapp = PlateSirnaGeneMapping(plate_file_set)
        return mapp

    def _integrate_platefileset(self, platefileset, features, mapping):
        """
        Iterate over all matlab files and create the final matrices

        :param platefileset: othe platefile set
        :param features: the parses feature map

        """
        logger.info("Integrating the different features to a single matrix")
        # since some features have different numbers of calls
        for k, v in features.items():
            self._integrate_feature(platefileset, k, v, mapping)

    def _integrate_feature(self, platefileset, max_ncells, features, mapping):
        filename = platefileset.outfile + "_max_nit_" + max_ncells + ".tsv"
        logger.info("Writing to: " + filename)
        pathogen = platefileset.pathogen
        library = platefileset.library
        library_vendor, library_type = list(library)
        replicate = platefileset.replicate
        screen = platefileset.screen
        plate = platefileset.plate
        layout = self._layout_meta.get(pathogen, library,
                                       screen, replicate,
                                       plate)
        with open(filename, "w") as f:
            header = PlateParser._meta + \
                     [feat.featurename.lower() for feat in features]
            # write the feature names
            f.write("\t".join(header) + "\n")
            # iterate over the different images
            # number of images per plate (should be 9 * 384)
            nimg = features[0].values.shape[0]
            assert nimg == len(mapping)
            for iimg in range(nimg):
                well = mapping[iimg]
                # number of cells in the iimg-th image
                ncells = features[0].ncells[iimg]
                # iterate over all the cells
                for cell in range(ncells):
                    # iterate over a single cell's feature
                    vals = [features[p].values[iimg, cell] for p in
                            range(len(features))]
                    meta = [pathogen, library_vendor, library_type, screen,
                            replicate, plate, layout.sirna(well),
                            layout.gene(well), well, layout.welltype(well),
                            iimg + 1, cell + 1]
                    f.write("\t".join(list(map(str, meta)) +
                                      list(map(str, vals))).lower() + "\n")
