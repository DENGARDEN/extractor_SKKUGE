import multiprocessing as mp
import os
import pathlib
import shlex
import subprocess as sp
import sys
from types import SimpleNamespace

import pandas as pd
from dask.diagnostics import ProgressBar
from icecream import ic

pbar = ProgressBar()
pbar.register()


class Helper(object):
    @staticmethod
    def mkdir_if_not(directory: pathlib.Path) -> pathlib.Path:
        """
        > If the directory doesn't exist, create it

        :param directory: The directory to create
        :type directory: str
        :return: A path object
        """
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def load_samples(directory: pathlib.Path) -> list:
        """
        It reads a file and returns a list of non-empty lines that don't start with a hash mark.

        :param directory: the directory of the samples file
        :type directory: pathlib.Path
        :return: A list of samples.
        """
        with open(directory, "r", encoding="utf-8") as file:
            lines = [line.strip("\n") for line in file.readlines()]
            sample_barcode_list = [
                line.split(",")[:2] for line in lines if line[0] != "#"
            ]

        return sample_barcode_list

    @staticmethod  # defensive
    def equal_num_samples_checker(
        proj_path: pathlib.Path, loaded_samples: list, logger
    ):
        """
        > This function checks if the number of samples in the Input folder and in the User folder
        matches

        :param proj_path: pathlib.Path, loaded_samples: list, logger
        :type proj_path: pathlib.Path
        :param loaded_samples: a list of sample names
        :type loaded_samples: list
        :param logger: a logger object
        """

        if len(list(proj_path.glob("*"))) != len(loaded_samples):
            logger.warning(
                "The number of samples in the Input folder and in the User folder does not matched. Check the file list in the Input folder and the project list in the User folder."
            )

            # input_entries = [i.name for i in proj_path.glob("*")]
            # user_entries = [i for i in loaded_samples]
            logger.warning(
                f"Input folder: {len(list(proj_path.glob('*')))}, Project list samples: {len(loaded_samples)}"
            )
            # logger.warning(
            #     f"Input folder: {[i for i in input_entries if i not in user_entries]}"
            # )
            # logger.warning(
            #     f"Project list samples: {[u for u in user_entries if u not in input_entries]}"
            # )
        else:
            logger.info("The file list is correct, pass\n")


class SystemStructure(object):
    def __init__(
        self,
        user_name: str,
        project_name: str,
        base_dir: pathlib.Path = pathlib.Path.cwd() / "Data",
    ):
        from collections import defaultdict
        from typing import DefaultDict

        # https://www.notion.so/dengardengarden/s-Daily-Scrum-Reports-74d406ce961c4af78366a201c1933b66#cd5b57433eca4c6da36145d81adbbe5e
        self.user_name = user_name
        self.project_name = project_name
        self.base_dir = base_dir
        self.input_sample_organizer: DefaultDict[str, pathlib.Path] = defaultdict(
            pathlib.Path
        )
        self.input_file_organizer: DefaultDict[str, pathlib.Path] = defaultdict(
            pathlib.Path
        )
        self.output_sample_organizer: DefaultDict[str, pathlib.Path] = defaultdict(
            pathlib.Path
        )

        self.user_dir = Helper.mkdir_if_not(
            self.base_dir / f'{"User" + "/" + self.user_name}'
        )
        self.barcode_dir = Helper.mkdir_if_not(self.base_dir / "Barcodes")
        self.input_dir = Helper.mkdir_if_not(
            self.base_dir
            / f'{"Input" + "/" + self.user_name + "/" + self.project_name}'
        )
        self.project_samples_path = pathlib.Path(
            self.user_dir / f"{self.project_name}.txt"
        )
        if not self.project_samples_path.exists():
            with open(self.project_samples_path, "w", encoding="utf-8") as f:
                f.write("# Sample,Barcode\n")

        self.output_dir = Helper.mkdir_if_not(
            self.base_dir
            / f'{"Output" + "/" + self.user_name + "/" + self.project_name}'
        )  # TODO is it needed?

    def mkdir_sample(self, sample_name: str, barcode_name: str):
        # TODO
        self.input_sample_organizer[sample_name] = Helper.mkdir_if_not(
            self.input_dir / sample_name
        )
        self.output_sample_organizer[sample_name] = Helper.mkdir_if_not(
            self.output_dir / barcode_name / sample_name
        )
        self.result_dir = Helper.mkdir_if_not(self.output_sample_organizer[sample_name])
        self.parquet_dir = Helper.mkdir_if_not(self.result_dir / "parquets")

        if len(os.listdir(f"{pathlib.Path.cwd() / self.parquet_dir}")) > 0:
            sp.run(
                [
                    "rm",
                    "-r",
                    f"{self.result_dir / 'parquets'}",
                ]
            )
            self.parquet_dir = Helper.mkdir_if_not(
                self.result_dir / "parquets"
            )  # Re-create the directory


# TODO: FLASh integration? https://ccb.jhu.edu/software/FLASH/
def fastp_integration():
    pass


class ExtractorRunner:
    def __init__(self, sample: str, barcode: str, args: SimpleNamespace):
        args.python = sys.executable
        # Find python executable if not specified
        args.system_structure.mkdir_sample(sample, pathlib.Path(barcode).name)
        self.sample = sample
        self.args = args

        for idx, file_path in enumerate(
            [
                p
                for p in self.args.system_structure.input_sample_organizer[
                    self.sample
                ].glob("*")
            ]
        ):
            # Load input file from input sample folder (only one file)
            if file_path.suffix in [".fastq", ".fq", ".fastq.gz", ".fq.gz"]:
                args.logger.info(f"File name : {file_path.stem}")
                self.args.system_structure.input_file_organizer[self.sample] = (
                    pathlib.Path.cwd() / file_path
                )
                break

            if (
                idx
                == len(
                    [
                        p
                        for p in self.args.system_structure.input_sample_organizer[
                            self.sample
                        ].glob("*")
                    ]
                )
                - 1
            ):
                raise Exception("No fastq file in the sample folder")

        # self.strInputList  => contains all splitted fastq file path; glob can be used

        self.args.system_structure.seq_split_dir = Helper.mkdir_if_not(
            self.args.system_structure.input_sample_organizer[self.sample]
            / "Split_files"
        )

        if (
            len(
                os.listdir(
                    f"{pathlib.Path.cwd() / self.args.system_structure.seq_split_dir}"
                )
            )
            > 0
        ):
            sp.run(
                [
                    "rm",
                    "-r",
                    f"{pathlib.Path.cwd() / self.args.system_structure.seq_split_dir}",
                ]
            )
            self.args.system_structure.seq_split_dir = Helper.mkdir_if_not(
                self.args.system_structure.input_sample_organizer[self.sample]
                / "Split_files"
            )  # Re-create the directory

    def _split_into_chunks(self):
        ### Defensive : original fastq wc == split fastq wc
        # https://docs.python.org/3.9/library/subprocess.html#security-considerations
        sp.run(
            shlex.split(
                shlex.quote(
                    f'split "{self.args.system_structure.input_file_organizer[self.sample]}" -l {4 * self.args.chunk_size} -d -a 6 --additional-suffix=.fastq {self.args.system_structure.seq_split_dir}/split_'
                )
            ),
            shell=True,
            check=True,
        )

        self.args.logger.info(
            f"The number of split files:{len(list(self.args.system_structure.seq_split_dir.glob('*')))}"
        )

    def _populate_command(self, barcode):
        return [
            (
                str(pathlib.Path.cwd() / self.args.system_structure.seq_split_dir / f),
                str(
                    pathlib.Path.cwd()
                    / self.args.system_structure.barcode_dir
                    / barcode
                ),
                self.args.logger,
                f"{(pathlib.Path(self.args.system_structure.result_dir) / 'parquets').absolute()}",
                self.args.sep,
            )
            for f in sorted(os.listdir(self.args.system_structure.seq_split_dir))
            if f.endswith(".fastq")
        ]


def system_struct_checker(func):
    def wrapper(args: SimpleNamespace):

        args.logger.info("System structure check : User, Project, Input, Output")
        args.multicore = os.cpu_count() if args.multicore == 0 else args.multicore
        if os.cpu_count() < args.multicore:
            args.logger.warning(
                f"Optimal threads <= {mp.cpu_count()} : {args.multicore} is not recommended"
            )
        for key, value in sorted(vars(args).items()):
            args.logger.info(f"Argument {key}: {value}")

        args.logger.info("File num check: input folder and project list")
        Helper.equal_num_samples_checker(
            args.system_structure.input_dir, args.samples, args.logger
        )

        return func(args)

    return wrapper


@system_struct_checker
def run_pipeline(args: SimpleNamespace) -> None:
    # TODO: add parquet remove option
    from dask import bag as db
    from dask import dataframe as dd
    from dask import delayed
    from dask.distributed import Client, LocalCluster, as_completed

    from Core.extractor import main as extractor_main

    args.logger.info("Initilaizing local cluster...")

    cluster = LocalCluster(
        processes=True,
        n_workers=mp.cpu_count(),
        threads_per_worker=1,
        memory_limit="2GB",
        dashboard_address=":40927",
    )
    client = Client(cluster)

    ic(client)
    ic(client.dashboard_link)

    read_count_futures = []
    for sample, barcode in args.samples:
        ExtractorRunner(
            sample, barcode, args
        )  # TODO: refactor its usage to avoid creating an object

        args.logger.info("Loading merged fastq file...")
        bag = db.read_text(args.system_structure.input_file_organizer[sample])
        sequence_ddf = bag.to_dataframe()
        sequence_ddf = (
            sequence_ddf.to_dask_array(lengths=True)
            .reshape(-1, 4)
            .to_dask_dataframe(
                columns=["ID", "Sequence", "Separator", "Quality"],
            )
        )

        # Load barcode file
        barcode_row_length = sum(1 for row in open(barcode, "r"))
        chunk_size = barcode_row_length // mp.cpu_count()
        args.logger.info("Loading barcode file...")
        barcode_df = pd.read_csv(
            barcode,
            sep=args.sep,
            header=None,
            names=["Gene", "Barcode"],
            chunksize=chunk_size,
        )

        args.logger.info("Submitting extraction process...")
        futures = []
        for i, barcode_chunk in enumerate(barcode_df):
            futures.append(
                client.submit(
                    extractor_main,
                    sequence_ddf,
                    barcode_chunk.iloc[:, [0, 1]],  # Use only Gene and Barcode columns
                    args.logger,
                    args.system_structure.result_dir,
                    args.sep,
                    chunk_number=i,
                )
            )
        args.logger.info("Gathering extraction results...")
        with ProgressBar():
            rvals = client.gather(futures)
        for rval in rvals:
            try:
                if rval == -1:
                    raise Exception(f"extractor_main has returned with {rval}")
            except ValueError:
                continue
                # args.logger.info("Barcode extraction completed")

        # Gather results
        # TODO  : Merge parquet files
        args.logger.info("Merging parquet files...")

        # # OPTION 1: extractor_main returns parquet file path
        all_extraction_delayed_datasts = []
        for file in rvals:
            all_extraction_delayed_datasts.append(
                delayed(dd.read_parquet)(
                    file,
                    engine="pyarrow",
                )
            )
        combined_extraction_datasets = (
            delayed(dd.concat)(
                all_extraction_delayed_datasts,
                axis=0,
            )
            .drop(columns=["ID"])
            .sum(axis=0)
        )

        combined_extraction_datasets.visualize(
            filename=f"{args.system_structure.result_dir}/read_counts.png"
        )

        read_count_futures.append(
            client.submit(combined_extraction_datasets.compute)
        )  # TODO: doing this job asynchronously

        args.logger.info(f"{sample}+{barcode}: Extraction future generated.")

    # After the loop
    pool = as_completed(read_count_futures, with_results=True)
    for future, result in pool:

        result.to_csv(
            f"{args.system_structure.output_sample_organizer[sample]}/'read_counts.csv'",
            index=True,
            single_file=True,
            compute=True,
        )
        ic(future) # DEBUG
