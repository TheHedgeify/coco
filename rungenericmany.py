#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Process data to be included in a generic template.

   Synopsis:
      python path_to_folder/bbob_pproc/runcompmany.py [OPTIONS] FOLDER_NAME...
    Help:
      python path_to_folder/bbob_pproc/runcompmany.py -h

"""

from __future__ import absolute_import

import os
import sys
import glob
import getopt
import pickle
import tarfile
from pdb import set_trace
import warnings
import numpy

# Add the path to bbob_pproc
if __name__ == "__main__":
    (filepath, filename) = os.path.split(sys.argv[0])
    sys.path.append(os.path.join(filepath, os.path.pardir))
    import matplotlib
    matplotlib.use('Agg') # To avoid window popup and use without X forwarding

from bbob_pproc import dataoutput, pproc
from bbob_pproc.dataoutput import algPlotInfos
from bbob_pproc.pproc import DataSetList, processInputArgs
from bbob_pproc.compall import ppperfprof, pptables, ppfigs
from bbob_pproc.compall import organizeRTDpictures

import matplotlib.pyplot as plt

# Used by getopt:
shortoptlist = "hvo:"
longoptlist = ["help", "output-dir=", "noisy", "noise-free", "tab-only",
               "per-only", "fig-only", "verbose", "settings="]
#CLASS DEFINITIONS

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

#FUNCTION DEFINITIONS

def usage():
    print main.__doc__

def main(argv=None):
    """Main routine for post-processing the data of multiple algorithms.

    Provided with some data, this routine outputs figure and TeX files in a
    folder needed for the compilation of latex document template3XXX.tex or
    noisytemplate3XXX, where XXX is either ecj or generic. The template file
    needs to be edited so that the command \\bbobdatapath points to the output
    folder.

    Provided with some data, this routine outputs figure and TeX files in a
    folder needed for the compilation of latex document template3XXX.tex, where
    XXX is either ecj or generic. The template file needs to be edited so that
    the command \\bbobdatapath points to the output folder.

    These output files will contain performance tables, performance scaling
    figures and empirical cumulative distribution figures. On subsequent
    executions, new files will be added to the output folder, overwriting
    existing older files in the process.

    Keyword arguments:
    argv -- list of strings containing options and arguments. If not provided,
    sys.argv is accessed.

    argv must list folders containing BBOB data files.
    The name of these folders will be used in the output figures and tables to
    designate the algorithms. Therefore you should name the folders with
    differentiating names.

    Furthermore, argv can begin with, in any order, facultative option flags
    listed below.

        -h, --help

            display this message

        -v, --verbose

            verbose mode, prints out operations, warnings. When not in verbose
            mode, only a little output is to be expected, except for errors.
            In case of error, we suggest providing with the output of the
            command with the addition of this option.

        -o, --output-dir OUTPUTDIR

            change the default output directory ('cmpmanydata') to OUTPUTDIR

        --noise-free, --noisy

            restrain the post-processing to part of the data set only.

        --settings SETTING

            change the style of the output figures and tables. At the moment
            only the only differences are in the colors of the output figures.
            SETTINGS can be either "grayscale", "color" or "black-white". The
            default setting is "color".

        --tab-only, --per-only, --fig-only

            these options can be used to output respectively the comparison
            TeX tables, the performance profiles or the figures of ERT/dim vs
            dim only. A combination of any two or more of these options results
            in no output.

    Exceptions raised:
    Usage -- Gives back a usage message.

    Examples:

    * Calling the rungenericmany.py interface from the command line:

        $ python bbob_pproc/rungenericmany.py -v AMALGAM BFGS BIPOP-CMA-ES


    * Loading this package and calling the main from the command line
      (requires that the path to this package is in python search path):

        $ python -m bbob_pproc.rungenericmany -h

    This will print out this help message.

    * From the python interactive shell (requires that the path to this
      package is in python search path):

        >>> from bbob_pproc import rungenericmany
        >>> rungenericmany.main('-o outputfolder folder1 folder2'.split())

    This will execute the post-processing on the data found in folder1 and
    folder2.
    The -o option changes the output folder from the default to outputfolder.

    * Generate post-processing data for some algorithms with figures in shades
      of gray:

        $ python rungenericmany.py --settings grayscale NEWUOA NELDER LSSTEP

    """

    if argv is None:
        argv = sys.argv[1:]

    try:
        try:
            opts, args = getopt.getopt(argv, shortoptlist, longoptlist)
        except getopt.error, msg:
             raise Usage(msg)

        if not (args):
            usage()
            sys.exit()

        verbose = False
        outputdir = 'ppdatamany'
        isNoisy = False
        isNoiseFree = False

        isPer = True
        isTab = True
        isFig = True
        inputsettings = "color"

        #Process options
        for o, a in opts:
            if o in ("-v","--verbose"):
                verbose = True
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-o", "--output-dir"):
                outputdir = a
            elif o == "--noisy":
                isNoisy = True
            elif o == "--noise-free":
                isNoiseFree = True
            #The next 3 are for testing purpose
            elif o == "--tab-only":
                isPer = False
                isFig = False
            elif o == "--per-only":
                isTab = False
                isFig = False
            elif o == "--fig-only":
                isPer = False
                isTab = False
            elif o == "--settings":
                inputsettings = a
            else:
                assert False, "unhandled option"

        # from bbob_pproc import bbob2010 as inset # input settings
        if inputsettings == "color":
            from bbob_pproc import genericsettings as inset # input settings
        elif inputsettings == "grayscale":
            from bbob_pproc import grayscalesettings as inset # input settings
        elif inputsettings == "black-white":
            from bbob_pproc import bwsettings as inset # input settings
        else:
            txt = ('Settings: %s is not an appropriate ' % inputsettings
                   + 'argument for input flag "--settings".')
            raise Usage(txt)

        if (not verbose):
            warnings.simplefilter('ignore')

        print ("BBOB Post-processing: will generate output " +
               "data in folder %s" % outputdir)
        print "  this might take several minutes."

        if not os.path.exists(outputdir):
            os.makedirs(outputdir)
            if verbose:
                print 'Folder %s was created.' % (outputdir)

        dsList, sortedAlgs, dictAlg = processInputArgs(args, verbose=verbose)

        if not dsList:
            sys.exit()

        for i in dictAlg:
            if isNoisy and not isNoiseFree:
                dictAlg[i] = dictAlg[i].dictByNoise().get('nzall', DataSetList())
            if isNoiseFree and not isNoisy:
                dictAlg[i] = dictAlg[i].dictByNoise().get('noiselessall', DataSetList())

        for i in dsList:
            if not i.dim in (2, 3, 5, 10, 20):
                continue

            if (dict((j, i.itrials.count(j)) for j in set(i.itrials)) <
                inset.instancesOfInterest):
                warnings.warn('The data of %s do not list ' %(i) +
                              'the correct instances ' +
                              'of function F%d.' %(i.funcId))

        plt.rc("axes", **inset.rcaxes)
        plt.rc("xtick", **inset.rctick)
        plt.rc("ytick", **inset.rctick)
        plt.rc("font", **inset.rcfont)
        plt.rc("legend", **inset.rclegend)

        # Performance profiles
        if isPer:
            # ECDFs per noise groups
            dictNoi = pproc.dictAlgByNoi(dictAlg)
            for ng, tmpdictAlg in dictNoi.iteritems():
                dictDim = pproc.dictAlgByDim(tmpdictAlg)
                for d, entries in dictDim.iteritems():
                    ppperfprof.main(entries, inset.summarized_target_function_values,
                                    order=sortedAlgs,
                                    plotArgs=algPlotInfos,
                                    outputdir=outputdir,
                                    info=('%02dD_%s' % (d, ng)),
                                    verbose=verbose)
            # ECDFs per function groups
            dictFG = pproc.dictAlgByFuncGroup(dictAlg)
            for fg, tmpdictAlg in dictFG.iteritems():
                dictDim = pproc.dictAlgByDim(tmpdictAlg)
                for d, entries in dictDim.iteritems():
                    ppperfprof.main(entries, inset.summarized_target_function_values,
                                    order=sortedAlgs,
                                    plotArgs=algPlotInfos,
                                    outputdir=outputdir,
                                    info=('%02dD_%s' % (d, fg)),
                                    verbose=verbose)
            print "ECDFs of ERT figures done."

        if isTab:
            dictNoi = pproc.dictAlgByNoi(dictAlg)
            for ng, tmpdictng in dictNoi.iteritems():
                dictDim = pproc.dictAlgByDim(tmpdictng)
                for d, tmpdictdim in dictDim.iteritems():
                    pptables.main(tmpdictdim, sortedAlgs,
                                  inset.tableconstant_target_function_values,
                                  outputdir, verbose)
            print "Comparison tables done."

        if isFig:
            plt.rc("axes", labelsize=20, titlesize=24)
            plt.rc("xtick", labelsize=20)
            plt.rc("ytick", labelsize=20)
            plt.rc("font", size=20)
            plt.rc("legend", fontsize=20)
            ppfigs.main(dictAlg, sortedAlgs, 1e-8, outputdir, verbose)
            plt.rcdefaults()
            print "Scaling figures done."

        plt.rcdefaults()

    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use -h or --help"
        return 2

if __name__ == "__main__":
    sys.exit(main())

