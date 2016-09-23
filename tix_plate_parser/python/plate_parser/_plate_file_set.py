# __author__ = 'Simon Dirmeier'
# __email__  = 'simon.dirmeier@bsse.ethz.ch'
# __date__   = 23/09/16

import random


class PlateFileSet:
    def __init__(self, classifier, outfile, pathogen,
                 library, replicate, plate, cid):
        self._classifier = classifier
        self._outfile = outfile
        self._pathogen = pathogen
        self._library = library
        self._replicate = replicate
        self._plate = plate
        self._cid = cid
        self._files = []

    def __iter__(self):
        for f in self._files:
            yield f

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "\t".join([self._pathogen, self._library, self._replicate,
                          self._plate, self._cid])

    def __len__(self):
        return len(self._files)

    def sample(self, cnt):
        return random.sample(self._files, cnt)

    @property
    def classifier(self):
        return self._classifier

    @property
    def files(self):
        return self._files
