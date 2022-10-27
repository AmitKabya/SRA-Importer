from __future__ import annotations

import getopt
import os
import pickle
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from chromedriver_py import binary_path

from .utilities import ReadsData, run_cmd, qiime2_version


def process_input(opts):
    opts = dict(opts)

    if '--output-dir' not in opts:
        print("output-dir is not found, and must be given")
        sys.exit(2)
    elif not (os.path.exists(opts['--output-dir']) and os.path.isdir(opts['--output-dir'])):
        print("The given output-dir does not exist")
        sys.exit(2)
    else:
        dir_path = opts['--output-dir']
        reads_data: ReadsData = pickle.load(open(os.path.join(dir_path, "reads_data.pkl"), "rb"))

    if '--trim' not in opts:
        print("trim is not found, and must be given")
        sys.exit(2)
    else:
        if reads_data.fwd and reads_data.rev:
            t = opts['--trim'].split(",")
            if len(t) != 2:
                print("The read consist of both forward and reverse, so 'trim' must be two non-negative integers.")
                sys.exit(2)
            if not (t[0].isnumeric() and t[1].isnumeric()):
                print("'trim' must get two non-negative integers.")
                sys.exit(2)
            trim = (int(t[0]), int(t[1]))
        else:
            t = opts['--trim'].split(",")
            if len(t) != 1:
                print("The read consist only forward, so 'trim' must be one non-negative integer.")
                sys.exit(2)
            if not opts['--trim'].isnumeric():
                print("'trim' must get one non-negative integer.")
                sys.exit(2)
            trim = int(opts['--trim'])

    if '--trunc' not in opts:
        print("trunc is not found, and must be given")
        sys.exit(2)
    else:
        if reads_data.fwd and reads_data.rev:
            t = opts['--trunc'].split(",")
            if len(t) != 2:
                print("The read consist of both forward and reverse, so 'trunc' must be two non-negative integers.")
                sys.exit(2)
            if not (t[0].isnumeric() and t[1].isnumeric()):
                print("'trunc' must get two non-negative integers.")
                sys.exit(2)
            trunc = (int(t[0]), int(t[1]))
        else:
            t = opts['--trunc'].split(",")
            if len(t) != 1:
                print("The read consist only forward, so 'trunc' must be one non-negative integer.")
                sys.exit(2)
            if not opts['--trunc'].isnumeric():
                print("'trunc' must get one non-negative integer.")
                sys.exit(2)
            trunc = int(opts['--trunc'])

    if '--threads' not in opts:
        threads = 12
    else:
        if not opts['--threads'].isnumeric() or opts['--threads'] == '0':
            print("'threads' must be a positive integer. set to default: threads=12")
            threads = 12
        else:
            threads = int(opts['--threads'])

    """otu-output-file=", "taxonomy-output-file="""
    if "--otu-output-file" not in opts:
        print("otu-output-file is not found, and must be given")
        sys.exit(2)
    else:
        t = opts["--otu-output-file"]
        dir_ = os.path.join(*os.path.split(t)[:-1])
        if not (os.path.exists(dir_) and os.path.isdir(dir_)):
            print(f"The directory of the file given in otu-output-file is not found. "
                  f"Create directory {dir_} or change to an existing one.")
            sys.exit(2)
        if t.split(".")[-1] not in {"tsv", 'txt'}:
            print(f"otu-output-file must be a tsv/txt file. Instead got a {t.split('.')[-1]} file.")
            sys.exit(2)
        otu_output_file = t

    if "--taxonomy-output-file" not in opts:
        print("taxonomy-output-file is not found, and must be given")
        sys.exit(2)
    else:
        t = opts["--taxonomy-output-file"]
        dir_ = os.path.join(*os.path.split(t)[:-1])
        if not (os.path.exists(dir_) and os.path.isdir(dir_)):
            print(f"The directory of the file given in taxonomy-output-file is not found. "
                  f"Create directory {dir_} or change to an existing one.")
            sys.exit(2)
        if t.split(".")[-1] != "tsv":
            print(f"taxonomy-output-file must be a tsv file. Instead got a {t.split('.')[-1]} file.")
            sys.exit(2)
        taxonomy_output_file = t

    return reads_data, trim, trunc, threads, otu_output_file, taxonomy_output_file


def qiime_dada2(reads_data: ReadsData, input_path: str,
                left: int | tuple[int, int], right: int | tuple[int, int], threads: int = 12):
    paired = reads_data.fwd and reads_data.rev

    trim_range = ["--p-trim-left-f", left[0], "--p-trim-left-r", left[1]] if paired \
        else ["--p-trim-left", left]
    trunc_range = ["--p-trunc-len-f", right[0], "--p-trunc-len-r", right[1]] if paired \
        else ["--p-trunc-len", right]

    command = [
                  "qiime", "dada2", "denoise-paired" if paired else "denoise-single",
                  "--i-demultiplexed-seqs", input_path,
              ] + trim_range + trunc_range + [
                  "--o-table", os.path.join(reads_data.dir_path, "qza", "dada2_table.qza"),
                  "--p-n-threads", threads,
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


def download_taxonomy_classifier(reads_data: ReadsData, qiime_version: str):
    options = webdriver.ChromeOptions()
    options.add_argument(f"download.default_directory={reads_data.dir_path}")
    options.add_argument(f"headless")

    service_object = Service(binary_path)
    driver = webdriver.Chrome(service=service_object, chrome_options=options)
    driver.get(f"https://data.qiime2.org/{qiime_version}/common/gg-13-8-99-nb-classifier.qza")


def assign_taxonomy(reads_data: ReadsData):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "feature-classifier", "classify-sklearn",
        "--i-reads", qza_path("rep-seqs-dn-99.qza"),
        "--i-classifier", os.path.join(reads_data.dir_path, "gg-13-8-99-nb-classifier.qza"),
        "--o-classification", qza_path("gg-13-8-99-nb-classified.qza")
    ]
    run_cmd(command)


def clean_taxonomy1(reads_data: ReadsData):
    qza_path = lambda filename: os.path.join(reads_data.dir_path, "qza", filename)
    command = [
        "qiime", "taxa", "filter-table",
        "--i-table", qza_path("table-dn-99.qza"),
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
        "-o", output_file
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


def main_importer():
    def usage():
        print(f"usage: export.py --output-dir <output-directory-path> --trim <trim-from> "
              f"--trunc <trunc-to> --threads <number-of-threads-to-use> "
              f"--otu-output-file <otu-output-file-path> --taxonomy-output-file <taxonomy-output-file-path>")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", ["output-dir=", "trim=", "trunc=",
                                                      "threads=", "otu-output-file=", "taxonomy-output-file="])
        reads_data, trim, trunc, threads, otu_output_file, taxonomy_output_file = process_input(opts)
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    paired = reads_data.rev and reads_data.fwd
    output_path = os.path.join(reads_data.dir_path, "qza", f"demux-{'paired' if paired else 'single'}-end.qza")

    qiime_dada2(reads_data, output_path, left=trim, right=trunc, threads=threads)

    cluster_features(reads_data)

    download_taxonomy_classifier(reads_data, qiime2_version().split("-")[1])

    assign_taxonomy(reads_data)

    run_cmd(["mkdir", os.path.join(reads_data.dir_path, "exports")])

    clean_taxonomy1(reads_data)
    clean_taxonomy2(reads_data)

    export_otu(reads_data, otu_output_file)
    export_taxonomy(reads_data, taxonomy_output_file)

    run_cmd(["conda", "deactivate"])
