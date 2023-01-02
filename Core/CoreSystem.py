import logging
import multiprocessing as mp
import os
import re
import subprocess as sp
import sys
from datetime import datetime
from pdb import set_trace
import pathlib

import numpy as np


#
# Camel case is not recommended to use in Python
#


class Helper(object):
    @staticmethod
    def MakeFolderIfNot(directory):
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def RemoveNullAndBadKeyword(Sample_list):
        listSamples = [
            strRow
            for strRow in Sample_list.readlines()
            if strRow not in ["''", "", '""', "\n", "\r", "\r\n"]
        ]
        return listSamples

    @staticmethod  ## defensive
    def CheckSameNum(strInputProject, listSamples):

        listProjectNumInInput = [
            i
            for i in sp.check_output(f"ls {strInputProject}", shell=False).split("\n")
            if i != ""
        ]

        setSamples = set(listSamples)
        setProjectNumInInput = set(listProjectNumInInput)

        intProjectNumInTxt = len(listSamples)
        intProjectNumInInput = len(listProjectNumInInput)

        if intProjectNumInTxt != len(setSamples - setProjectNumInInput):
            logging.warning(
                "The number of samples in the input folder and in the project list does not matched."
            )
            logging.warning(
                f"Input folder: {intProjectNumInInput}, Project list samples: {intProjectNumInTxt}"
            )
            raise AssertionError
        else:
            logging.info("The file list is correct, pass\n")

    @staticmethod  ## defensive
    def CheckAllDone(strOutputProject, listSamples):
        intProjectNumInOutput = len(
            [
                i
                for i in sp.check_output("ls %s" % strOutputProject, shell=False).split(
                    "\n"
                )
                if i not in ["All_results", "Log", ""]
            ]
        )

        if intProjectNumInOutput != len(listSamples):
            logging.warning(
                "The number of samples in the output folder and in the project list does not matched."
            )
            logging.warning(
                "Output folder: %s, Project list samples: %s\n"
                % (intProjectNumInOutput, len(listSamples))
            )
        else:
            logging.info("All output folders have been created.\n")

    @staticmethod
    def SplitSampleInfo(strSample):

        if strSample[0] == "#":
            return False
        logging.info("Processing sample : %s" % strSample)
        lSampleRef = (
            strSample.replace("\n", "").replace("\r", "").replace(" ", "").split("\t")
        )

        if len(lSampleRef) == 2:
            strSample = lSampleRef[0]
            strRef = lSampleRef[1]
            return (strSample, strRef, "")

        elif len(lSampleRef) == 3:
            strSample = lSampleRef[0]
            strRef = lSampleRef[1]
            strExpCtrl = lSampleRef[2].upper()
            return (strSample, strRef, strExpCtrl)

        else:
            logging.error(
                "Confirm the file format is correct. -> Sample name\tReference name\tGroup"
            )
            logging.error("Sample list input : %s\n" % lSampleRef)
            raise Exception

    @staticmethod
    def CheckIntegrity(strBarcodeFile, strSeq):  ## defensive
        rec = re.compile(r"[A|C|G|T|N]")

        if ":" in strSeq:
            strSeq = strSeq.split(":")[1]

        strNucle = re.findall(rec, strSeq)
        if len(strNucle) != len(strSeq):
            logging.error(
                "This sequence is not suitable, check A,C,G,T,N are used only : %s"
                % strBarcodeFile
            )
            set_trace()
            sys.exit(1)

    @staticmethod
    def PreventFromRmMistake(strCmd):
        rec = re.compile(
            r"rm.+-rf*.+(\.$|\/$|\*$|User$|Input$|Output$)"
        )  ## This reg can prevent . / * ./User User ...
        if re.findall(rec, strCmd):
            raise Exception("%s is critical mistake! never do like this." % strCmd)


class SystemStructureChecker(object):
    def __init__(
        self,
        user_name: str,
        project_name: str,
    ):
        self.user_name = user_name
        self.project_name = project_name

        Helper.MakeFolderIfNot("User" / self.user_name)
        Helper.MakeFolderIfNot("Barcodes")

    def MakeInputFolder(self):
        Helper.MakeFolderIfNot("Input" / self.user_name / "FASTQ" / self.project_name)
        self.project_samples = pathlib.Path(
            "User" / self.user_name / f"{self.project_name}.txt"
        )
        if not self.project_samples.exists():
            with open(self.project_samples, "w") as f:
                f.write("")

    def MakeOutputFolder(self):

        ## './Output/JaeWoo'
        Helper.MakeFolderIfNot("Output" / self.user_name / self.project_name)
        strOutputUserDir = f"./Output/{self.user_name}"
        Helper.MakeFolderIfNot(strOutputUserDir)

        ## './Output/JaeWoo/Test_samples'
        self.strOutputProjectDir = os.path.join(strOutputUserDir, self.project_name)
        Helper.MakeFolderIfNot(self.strOutputProjectDir)

        ## './Output/JaeWoo/Test_samples/Log'
        strOutputLog = os.path.join(self.strOutputProjectDir, "Log")
        Helper.MakeFolderIfNot(strOutputLog)

        strLogName = (
            str(datetime.now())
            .replace("-", "_")
            .replace(":", "_")
            .replace(" ", "_")
            .split(".")[0]
        )
        self.strLogPath = os.path.join(
            self.strOutputProjectDir, f"Log/{strLogName}_log.txt"
        )


class UserFolderAdmin(object):
    """
    InitialFolder : out of the loop
    UserFolderAdmin : in the loop

    So InitialFolder and UserFolderAdmin must be distinguished.
    """

    def __init__(self, strSample, strRef, options, strLogPath):
        self.strSample = strSample
        self.strRef = strRef
        self.strLogPath = strLogPath

        self.user_name = options.user_name
        self.project_name = options.project_name

        self.intCore = options.multicore
        self.strGapOpen = options.gap_open  # CRISPresso aligner option
        self.strGapExtend = options.gap_extend  #
        self.strPython = options.python

        self.strOutProjectDir = ""
        self.strOutSampleDir = ""
        self.strRefDir = ""

    def MakeSampleFolder(self):
        ## './Output/Jaewoo/Test_samples'
        self.strOutProjectDir = "./Output/{user}/{project}".format(
            user=self.user_name, project=self.project_name
        )

        ## './Output/Jaewoo/Test_samples/Sample_1'
        self.strOutSampleDir = os.path.join(self.strOutProjectDir, self.strSample)
        Helper.MakeFolderIfNot(self.strOutSampleDir)

        ## './Output/Jaewoo/Test_samples/Sample_1/Tmp'
        Helper.MakeFolderIfNot(os.path.join(self.strOutSampleDir, "Tmp"))

        ## './Output/Jaewoo/Test_samples/Sample_1/Tmp/Pickle'
        Helper.MakeFolderIfNot(os.path.join(self.strOutSampleDir, "Tmp/Pickle"))

        ## './Output/Jaewoo/Test_samples/Sample_1/Result'
        Helper.MakeFolderIfNot(os.path.join(self.strOutSampleDir, "Result"))

        ## './Output/Jaewoo/Test_samples/All_results
        strAllResultDir = os.path.join(self.strOutProjectDir, "All_results")
        Helper.MakeFolderIfNot(strAllResultDir)

        self.strRefDir = "./Input/{user}/Reference/{project}/{ref}".format(
            user=self.user_name, project=self.project_name, ref=self.strRef
        )


class CoreHash(object):
    @staticmethod
    def MakeHashTable(strSeq, intBarcodeLen):
        listSeqWindow = [
            strSeq[i : i + intBarcodeLen]
            for i in range(len(strSeq))[: -intBarcodeLen - 1]
        ]
        return listSeqWindow

    @staticmethod
    def IndexHashTable(dictRef, strSeqWindow, intFirstBarcode):
        lCol_ref = dictRef[strSeqWindow]
        strBarcode = strSeqWindow
        intFirstBarcode = 1

        return (lCol_ref, strBarcode, intFirstBarcode)


class CoreGotoh(object):
    def __init__(self, strEDNAFULL="", floOg="", floOe=""):
        self.npAlnMatrix = CRISPResso2Align.read_matrix(strEDNAFULL)
        self.floOg = floOg
        self.floOe = floOe

    def GapIncentive(self, strRefSeqAfterBarcode):
        ## cripsress no incentive == gotoh
        intAmpLen = len(strRefSeqAfterBarcode)
        npGapIncentive = np.zeros(intAmpLen + 1, dtype=np.int)
        return npGapIncentive

    def RunCRISPResso2(
        self, strQuerySeqAfterBarcode, strRefSeqAfterBarcode, npGapIncentive
    ):
        listResult = CRISPResso2Align.global_align(
            strQuerySeqAfterBarcode.upper(),
            strRefSeqAfterBarcode.upper(),
            matrix=self.npAlnMatrix,
            gap_open=self.floOg,
            gap_extend=self.floOe,
            gap_incentive=npGapIncentive,
        )
        return listResult


def CheckProcessedFiles(Func):
    def Wrapped_func(**kwargs):
        # kwargs
        # InstInitFolder = InstInitFolder,
        # strInputProject = strInputProject,
        # intProjectNumInTxt = intProjectNumInTxt,
        # listSamples = listSamples,
        # logging = logging

        InstInitFolder = kwargs["InstInitFolder"]
        strInputProject = kwargs["strInputProject"]
        listSamples = kwargs["listSamples"]
        logging = kwargs["logging"]

        logging.info("File num check: input folder and project list")
        Helper.CheckSameNum(strInputProject, listSamples)

        Func(**kwargs)

        logging.info("Check that all folder are well created.")
        Helper.CheckAllDone(InstInitFolder.strOutputProjectDir, listSamples)

    return Wrapped_func


def AttachSeqToIndel(
    strSample, strBarcodeName, strIndelPos, strRefseq, strQueryseq, dictSub
):
    listIndelPos = strIndelPos.split("M")
    intMatch = int(listIndelPos[0])

    if "I" in strIndelPos:
        intInsertion = int(listIndelPos[1].replace("I", ""))
        strInDelSeq = strQueryseq[intMatch : intMatch + intInsertion]

    elif "D" in strIndelPos:
        intDeletion = int(listIndelPos[1].replace("D", ""))
        strInDelSeq = strRefseq[intMatch : intMatch + intDeletion]

    else:
        logging.info(
            "strIndelClass is included I or D. This variable is %s" % strIndelPos
        )
        raise Exception

    strInDelPosSeq = strIndelPos + "_" + strInDelSeq

    try:
        _ = dictSub[strSample][strBarcodeName]
    except KeyError:
        dictSub[strSample][strBarcodeName] = {}

    try:
        dictSub[strSample][strBarcodeName][strBarcodeName + ":" + strInDelPosSeq][
            "IndelCount"
        ] += 1
    except KeyError:
        dictSub[strSample][strBarcodeName][strBarcodeName + ":" + strInDelPosSeq] = {
            "IndelCount": 1
        }


def RunProgram(sCmd):
    sp.call(sCmd, shell=False)


def RunMulticore(lCmd, iCore):
    for sCmd in lCmd:
        print(sCmd)

    p = mp.Pool(iCore)
    p.map_async(RunProgram, lCmd).get()
    p.close()
