#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original code is here, https://github.com/MyungjaeSong/Paired-Library.git
# This is the modified version of the program for academic uses in SKKUGE Lab

__author__ = "forestkeep21@naver.com"
__editor__ = "poowooho3@g.skku.edu"

import time
import pathlib

import pandas as pd
from tqdm import tqdm
import skbio

from Core.CoreSystem import SystemStructure


def extract_read_cnts(
    sequence_file: pathlib.Path,
    barcode_file: pathlib.Path,
) -> pd.DataFrame:
    # df index == barcode, column == read count

    tqdm.pandas()
    # Load barcode file
    result_df = pd.read_csv(
        barcode_file, sep=":", header=None, names=["Gene", "Barcode"]
    ).set_index(
        "Gene"
    )  # TODO: tentative design

    # Load a splitted sequencing result using high-level I/O
    seqs = skbio.io.read(
        sequence_file, format="fastq", verify=True, variant="illumina1.8"
    )  # FASTQ format verification using skbio

    seq_df = pd.DataFrame([seq._string.decode() for seq in seqs], columns=["Sequence"])
    result_df["Read_counts"] = 0
    print()
    for idx, row in tqdm(result_df.iterrows()):
        result_df.loc[idx, "Read_counts"] = (
            seq_df["Sequence"].str.contains(row["Barcode"]).sum()
        )

    # result_df example
    #                                             Barcode  Read_counts
    # Gene
    # Frag1_Pos_1_M_F     TTCACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_Y     TACACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_C     TGCACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_STOP  TGAACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_W     TGGACTGAATATAAACTTGTGGTAGTT            0

    return result_df


def main(*args) -> pd.DataFrame:
    (sequence, barcode, logger) = args[0]

    start = time.time()
    rval = extract_read_cnts(sequence, barcode)
    end = time.time()

    logger.info(f"Extraction is done. {end - start}s elapsed.")

    return rval
