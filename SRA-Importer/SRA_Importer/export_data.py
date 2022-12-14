from __future__ import annotations

import datetime
import os
import pickle

from .utilities import ReadsData, run_cmd, download_classifier_url, check_conda_qiime2


def trim_trunc_check(reads_data: ReadsData, trim: int | tuple[int, int], trunc: int | tuple[int, int]):
    if reads_data.fwd and reads_data.rev:
        if not isinstance(trim, tuple) or not isinstance(trunc, tuple):
            raise TypeError("The read consist of both forward and reverse, "
                            "so 'trim' and 'trunc' must be tuples of integers.\n"
                            f"Got {type(trim)}, {type(trunc)}.")

        if len(trim) != 2 or len(trunc) != 2:
            raise ValueError("The read consist of both forward and reverse, "
                             "so 'trim' and 'trunc' must be tuples of 2 integers.\n"
                             f"Got tuples of length {len(trim)}, {len(trunc)}.")
    if not isinstance(trim, int) or not isinstance(trunc, int):
        raise TypeError("The read consist of only forward, "
                        "so 'trim' and 'trunc' must be integers.\n"
                        f"Got {type(trim)}, {type(trunc)}.")


def classifier_exists(classifier_path: str):
    if not (os.path.exists(classifier_path) and os.path.isfile(classifier_path)):
        raise FileNotFoundError("Classifier not found! Please give the right path to the classifier.\n"
                                f"Download it from: {download_classifier_url()}")


def output_files_check(otu_output_file: str, taxonomy_output_file: str):
    dir_ = os.path.join(*os.path.split(otu_output_file)[:-1])
    if not (os.path.exists(dir_) and os.path.isdir(dir_)):
        raise NotADirectoryError(f"The directory of the file given in otu_output_file is not found. "
                                 f"Create directory {dir_} or change to an existing one.")

    if otu_output_file.split(".")[-1] not in {"tsv", 'txt'}:
        raise ValueError(f"otu_output_file must be a tsv/txt file. "
                         f"Instead got a {otu_output_file.split('.')[-1]} file.")

    dir_ = os.path.join(*os.path.split(taxonomy_output_file)[:-1])
    if not (os.path.exists(dir_) and os.path.isdir(dir_)):
        raise NotADirectoryError(f"The directory of the file given in taxonomy_output_file is not found. "
                                 f"Create directory {dir_} or change to an existing one.")

    if taxonomy_output_file.split(".")[-1] != "tsv":
        raise ValueError(f"taxonomy_output_file must be a tsv file. "
                         f"Instead got a {taxonomy_output_file.split('.')[-1]} file.")


def qiime_dada2(reads_data: ReadsData, input_path: str,
                left: int | tuple[int, int], right: int | tuple[int, int], threads: int = 12):
    paired = reads_data.fwd and reads_data.rev

    trim_range = ["--p-trim-left-f", str(left[0]), "--p-trim-left-r", str(left[1])] if paired \
        else ["--p-trim-left", str(left)]
    trunc_range = ["--p-trunc-len-f", str(right[0]), "--p-trunc-len-r", str(right[1])] if paired \
        else ["--p-trunc-len", str(right)]

    command = [
                  "qiime", "dada2", "denoise-paired" if paired else "denoise-single",
                  "--i-demultiplexed-seqs", input_path,
              ] + trim_range + trunc_range + [
                  "--o-table", os.path.join(reads_data.dir_path, "qza", "dada2_table.qza"),
                  "--p-n-threads", str(threads),
                  "--p-chimera-method", "consensus",
                  "--o-representative-sequences", os.path.join(reads_data.dir_path, "qza", "dada2_rep-seqs.qza"),
                  "--o-denoising-stats", os.path.join(reads_data.dir_path, "qza", "dada2_denoising-stats.qza"),
              ]
    run_cmd(command)


def cluster_features(reads_data: ReadsData):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "vsearch", "cluster-features-de-novo",
        "--i-table", qza_path("dada2_table.qza"),
        "--i-sequences", qza_path("dada2_rep-seqs.qza"),
        "--p-perc-identity", "0.99",
        "--o-clustered-table", qza_path("table-dn-99.qza"),
        "--o-clustered-sequences", qza_path("rep-seqs-dn-99.qza")
    ]
    run_cmd(command)


def assign_taxonomy(reads_data: ReadsData, classifier_path: str):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "feature-classifier", "classify-sklearn",
        "--i-reads", qza_path("rep-seqs-dn-99.qza"),
        "--i-classifier", classifier_path,
        "--o-classification", qza_path("gg-13-8-99-nb-classified.qza")
    ]
    run_cmd(command)


def clean_taxonomy1(reads_data: ReadsData):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "taxa", "filter-table",
        "--i-table", qza_path("table-dn-99.qza"),
        "--i-taxonomy", qza_path("gg-13-8-99-nb-classified.qza"),
        "--p-exclude", "mitochondria,chloroplast",
        "--o-filtered-table", qza_path("clean_table.qza")
    ]
    run_cmd(command)


def clean_taxonomy2(reads_data: ReadsData):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "feature-table", "filter-features",
        "--i-table", qza_path("clean_table.qza"),
        "--p-min-samples", "3",
        "--p-min-frequency", "10",
        "--o-filtered-table", qza_path("feature-frequency-filtered-table.qza")
    ]
    run_cmd(command)


def export_otu(reads_data: ReadsData, output_file: str):
    # export
    command = [
        "qiime", "tools", "export",
        "--input-path", os.path.join(reads_data.dir_path, "qza", "feature-frequency-filtered-table.qza"),
        "--output-path", os.path.join(reads_data.dir_path, "exports")
    ]
    run_cmd(command)

    # convert
    command = [
        "biom", "convert",
        "-i", os.path.join(reads_data.dir_path, "exports", "feature-table.biom"),
        "-o", output_file,
        "--to-tsv"
    ]
    run_cmd(command)


def export_taxonomy(reads_data: ReadsData, output_file: str):
    # export
    command = [
        "qiime", "tools", "export",
        "--input-path", os.path.join(reads_data.dir_path, "qza", "gg-13-8-99-nb-classified.qza"),
        "--output-path", os.path.join(reads_data.dir_path, "exports")
    ]
    run_cmd(command)

    # copy taxonomy.tsv to output_file
    command = ["cp", os.path.join(reads_data.dir_path, "exports", "taxonomy.tsv"), output_file]
    run_cmd(command)


def export(*, output_dir: str, trim: int | tuple[int, int], trunc: int | tuple[int, int], classifier_file: str,
           otu_output_file: str, taxonomy_output_file: str, threads: int = 12):
    check_conda_qiime2()

    reads_data: ReadsData = pickle.load(open(os.path.join(output_dir, "reads_data.pkl"), "rb"))
    trim_trunc_check(reads_data, trim, trunc)
    output_files_check(otu_output_file, taxonomy_output_file)
    classifier_exists(classifier_file)

    paired = reads_data.rev and reads_data.fwd
    output_path = os.path.join(reads_data.dir_path, "qza", f"demux-{'paired' if paired else 'single'}-end.qza")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start dada2 (1/6)")
    qiime_dada2(reads_data, output_path, left=trim, right=trunc, threads=threads)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish dada2 (1/6)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start clustering features (2/6)")
    cluster_features(reads_data)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish clustering features (2/6)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start assigning taxonomy (3/6)")
    assign_taxonomy(reads_data, classifier_file)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish assigning taxonomy (3/6)")

    run_cmd(["mkdir", os.path.join(reads_data.dir_path, "exports")])

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start cleaning taxonomy (4/6)")
    clean_taxonomy1(reads_data)
    clean_taxonomy2(reads_data)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish cleaning taxonomy (4/6)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start exporting OTU (5/6)")
    export_otu(reads_data, otu_output_file)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish exporting OTU (5/6)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start exporting taxonomy (6/6)")
    export_taxonomy(reads_data, taxonomy_output_file)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish exporting taxonomy (6/6)")
