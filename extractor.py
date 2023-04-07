#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original code is here, https://github.com/MyungjaeSong/Paired-Library.git
# This is the modified version of the program for academic uses in SKKUGE Lab

__author__ = "forestkeep21@naver.com"
__editor__ = "poowooho3@g.skku.edu"

import pathlib

import pandas as pd
from tqdm import tqdm
import skbio
import gc


def extract_read_cnts(
    sequence_file: pathlib.Path, barcode_file: pathlib.Path, result_dir
) -> None:
    # df index == barcode, column == read count

    from torch import cuda
    from dask.dataframe import from_pandas as dask_from_pandas

    tqdm.pandas()
    # Load barcode file
    result_df = pd.read_csv(
        barcode_file, sep=":", header=None, names=["Gene", "Barcode"]
    )
    result_df["Barcode_copy"] = result_df["Barcode"]
    result_df = result_df.set_index("Barcode")  # TODO: tentative design

    # Load a split sequencing result using high-level I/O; validating fastq format
    result_df["Read_counts"] = 0
    result_df["ID"] = ""
    seqs = skbio.io.read(
        sequence_file, format="fastq", verify=True, variant="illumina1.8"
    )  # FASTQ format verification using skbio
    # cuda_available = cuda.is_available()
    cuda_available = False

    # debug
    if cuda_available:
        import cudf

        # print("Nvidia GPU detected!")

        seq_df = cudf.DataFrame(
            [(seq.metadata["id"], seq._string.decode()) for seq in seqs],
            columns=["ID", "Sequence"],
        )

        for idx, row in tqdm(result_df.iterrows()):
            query_result = seq_df["Sequence"].str.contains(row["Barcode_copy"])
            (
                result_df.loc[idx, "ID"],
                result_df.loc[idx, "Sequence"],
                result_df.loc[idx, "Read_counts"],
            ) = (
                "\n".join(
                    seq_df.loc[query_result[query_result].index]["ID"]
                    .to_numpy()
                    .tolist()
                ),
                "\n".join(
                    seq_df.loc[query_result[query_result].index]["Sequence"]
                    .to_numpy()
                    .tolist()
                ),
                query_result.sum(),
            )  # boolean indexing for fast processing

    else:  # this command not being found can raise quite a few different errors depending on the configuration
        # print("No Nvidia GPU in system!")

        seq_df = pd.DataFrame(
            [(seq.metadata["id"], seq._string.decode()) for seq in seqs],
            columns=["ID", "Sequence"],
        )
        for idx, row in tqdm(result_df.iterrows()):
            query_result = seq_df["Sequence"].str.contains(row["Barcode_copy"])
            result_df.at[idx, "ID"], result_df.loc[idx, "Read_counts"] = (
                seq_df.loc[query_result[query_result].index]["ID"].to_numpy().tolist(),
                query_result.sum(),
            )  # boolean indexing for fast processing
    del seq_df
    gc.collect()

    result_df.drop("Barcode_copy", axis=1, inplace=True)
    result_df.reset_index(inplace=True, drop=False)
    result_df.iloc[1], result_df.iloc[-1] = result_df.iloc[-1], result_df.iloc[1]

    def name():
        from datetime import datetime

        dt_string = datetime.now().strftime("%Y-%m-%d;%H:%M:%S")
        return str(f"{dt_string}")

    result_df.to_parquet(
        f"{result_dir}/{name()}+{pathlib.Path(sequence_file).name}.parquet"
    )

    del result_df
    gc.collect()
    return
    # result_df example
    #                                             Barcode  Read_counts
    # Gene
    # Frag1_Pos_1_M_F     TTCACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_Y     TACACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_C     TGCACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_STOP  TGAACTGAATATAAACTTGTGGTAGTT            0
    # Frag1_Pos_1_M_W     TGGACTGAATATAAACTTGTGGTAGTT            0


def main(*args) -> pd.DataFrame:
    (sequence, barcode, logger, result_dir) = args[0]

    # start = time.time()
    rval = extract_read_cnts(sequence, barcode, result_dir)
    # end = time.time()

    # logger.info(f"Extraction is done. {end - start}s elapsed.")

    return rval
