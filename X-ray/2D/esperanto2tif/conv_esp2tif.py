__author__ = 'Konstantin Glazyrin'

import os
import re
import sys
import argparse
import logging
import struct
import copy

def main():
    conv = Converter(sys.argv)
    conv.start()

class Logger(object):
    def __init__(self, level=logging.DEBUG):
        self.__logger = logging.getLogger(name=self.__class__.__name__)
        self.__logger.setLevel(level)

        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        self.__logger.addHandler(sh)

    def error(self, msg):
        self.__logger.error(unicode(msg))
        exit(-1)

    def info(self, msg):
        self.__logger.info(unicode(msg))

    def debug(self, msg):
        self.__logger.debug(unicode(msg))

    def warn(self, msg):
        self.__logger.warn(unicode(msg))

    def critical(self, msg):
        self.__logger.critical(unicode(msg))
        exit(-1)

class Converter(Logger):
    TEMPLATE_TIF = "template_tif.tif"
    TIF_HEADER = 8  # byte length of template header in TEMPLATE_TIF
    TIF_WIDTH_OFFSET = 10
    TIF_HEIGHT_OFFSET = 10

    ESPERANTO = "esperanto"
    def __init__(self, args, level=logging.DEBUG):
        Logger.__init__(self, level=level)

        self._header = []
        self._footer = []

        self._filenames = None

        self._floats = []

        self._parser = None
        self._args = None

        self.initialize()

    def initialize(self):
        self._init_parser()
        self._init_template()

    def _init_parser(self):
        """
        Initializes parser, parses arguments
        :return:
        """
        self._parser = argparse.ArgumentParser(description="Convertor from ESPERANTO to TIF", usage='%(prog)s [options]')
        self._parser.add_argument('input_file', metavar='if', type=unicode, help="input ESPERANTO type filenames", nargs='+')

        self._args = self._parser.parse_args()

        self.debug("------------ Testing input files")
        try:
            self._filenames = self._args.input_file

            if not isinstance(self._filenames, list):
                self._filenames = [self._filenames]

            for fn in self._filenames:
                if not os.path.isfile(fn):
                    raise AttributeError, fn
                self.debug("Filename {0} exists".format(fn))
        except AttributeError as e:
            self.error("Filename does not exist please check - {0})".format(e))

    def _init_template(self):
        """
        Byte wise reads TIF template, stores information in memory
        :return:
        """
        try:
            self.debug("------------ Testing TIF template")
            if not os.path.isfile(self.TEMPLATE_TIF):
                raise AttributeError

            counter = 0
            with open(self.TEMPLATE_TIF, 'rb') as fh:
                while True:
                    byte = fh.read(1)

                    if byte == b'':
                        break

                    # header
                    if counter < self.TIF_HEADER:
                        self._header.append(byte)
                    else: # footer
                        self._footer.append(byte)

                    counter += 1

            self.debug("TIF Header length - {0} Bytes".format(len(self._header)))
            self.debug("TIF Footer length - {0} Bytes".format(len(self._footer)))

        except AttributeError:
            self.error("TIF Template Filename does not exist ({0})".format(self.TEMPLATE_TIF))

    def start(self):
        """
        Starts conversion - tests file format, moves binary file contents to memory, converts integers to floats,
        dumps data to file with new extension
        :return:
        """
        self.debug("------------ Starting conversion: in total {0} files".format(len(self._filenames)))
        for (i, filename) in enumerate(self._filenames):
            basename, fext = os.path.splitext(filename)
            self.debug("{0}: {1} -> {2}.tif".format(i+1, filename, basename))

            # testing esperanto format
            try:
                self.read_esperanto_write_tif(filename, basename)
            except ValueError:
                self.warn("File ({0}) is not an ESPERANTO file".format(filename))
                continue

    def read_esperanto_write_tif(self, filename, basename):
        """
        Performs a quick test of file format, reads data into the memory
        :return:
        """
        floats = []
        w, h = 0, 0

        self.debug("Checking file {0}".format(filename))
        with open(filename, 'rb') as fh:

            #checking format
            fline = fh.read(256)
            self.debug("{0} header info: {1}".format(filename, fline.strip()))

            if not self.ESPERANTO.lower() in fline.lower():
                raise ValueError

            # skip the rest of the file header
            header = fh.read(256*24)

            patt = re.compile('IMAGE\s+([0-9]+)\s+([0-9]+)')

            match = patt.match(header)
            if match:
                w, h = match.groups()

                try:
                    w, h = int(w), int(h)
                except ValueError:
                    w, h = 0, 0
                self.debug("{0} header detector info:  Width:Height ({1}:{2})".format(filename, w, h))

            # reading contents of the file to the memory - 4 bytes integer is anticipated
            self.debug("Reading ESPERANTO file".format(filename))
            try:
                while True:
                    buffer = []
                    for i in range(4):
                        byte =  fh.read(1)
                        if byte == b'':
                            raise EOFError

                        buffer.append(byte)

                    idata = struct.unpack("<i", "".join(buffer))[0]
                    floats.append(struct.pack("<f", float(idata)))

            except EOFError:
                pass
            finally:
                self.debug("Test width*height={0}, {1} fields have been read; Test successful: {2}".format(w*h, len(floats), w*h==len(floats)))

                if w*h!=len(floats):
                    self.warn("{0} - has strange content, width or height are different from expected".format(filename))

        # file has been read, writing
        filename = "{0}.tif".format(basename)
        self.debug("Saving information into {0}".format(filename))

        # update footer - change width+height
        w, h = struct.pack("<i", w), struct.pack("<i", h)

        header, footer = copy.copy(self._header), copy.copy(self._footer)

        for i in range(len(w)):
            footer[self.TIF_WIDTH_OFFSET+i] = w[i]
            footer[self.TIF_HEIGHT_OFFSET+i] = h[i]

        # write data to esperanto
        header, footer = ''.join(header), ''.join(footer)
        with open(filename, 'wb') as fh:
            fh.write(header)
            fh.write(''.join(floats))
            fh.write(footer)

        self.debug("Conversion of file {0} has finished successfully".format(filename))


if __name__=="__main__":
    main()

#@TODO - saving detector dimensions