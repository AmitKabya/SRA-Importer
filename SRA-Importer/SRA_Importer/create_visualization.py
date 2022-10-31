from __future__ import annotations

import csv
import os.path
import pickle
import datetime
from tqdm import tqdm

from .utilities import run_cmd, ReadsData, check_conda_qiime2

CONDA_PREFIX = os.environ.get("CONDA_PREFIX", None)


def check_input(acc_list: str, output_vis_path: str):
    if not (os.path.exists(acc_list) and os.path.isfile(acc_list)):
        FileNotFoundError("The given acc_list does not exist or is not a file.")

    t = os.path.join(*os.path.split(output_vis_path)[:-1])
    if not (os.path.exists(t) and os.path.isdir(t)):
        print("WARNING: Invalid output_vis_path. output_vis_path must be located in an existing directory."
              "\noutput_vis_path will be saved in default location, under the created direction inside 'vis'")

    if output_vis_path.split(".")[-1] != "qzv":
        print("WARNING: Invalid output_vis_path. output-vis-path must be a qzv file."
              "\noutput-vis-path will be saved in default location, under the created direction inside 'vis'")


def download_data_from_sra(dir_path: str, acc_list: str = ""):
    """
    return True if downloaded the data successfully, False O/W
    """
    run_cmd(["mkdir", os.path.join(dir_path, "sra")])
    run_cmd(['prefetch', "--option-file", acc_list, "--output-directory", os.path.join(dir_path, "sra")])


def sra_to_fastq(dir_path: str):
    run_cmd(["mkdir", os.path.join(dir_path, "fastq")])
    for sra_dir in tqdm(os.listdir(os.path.join(dir_path, "sra")), desc="converted files"):
        sra_file = os.listdir(os.path.join(dir_path, "sra", sra_dir))[0]
        sra_path = os.path.join(dir_path, "sra", sra_dir, sra_file)
        fastq_path = os.path.join(dir_path, "fastq")
        run_cmd(["fasterq-dump", "--split-files", sra_path, "-O", fastq_path])

    # check if reads include fwd and rev
    fastqs = sorted(os.listdir(os.path.join(dir_path, "fastq")))[:3]
    if len(set([fastq.split("_")[0] for fastq in fastqs])) == 1:
        return ReadsData(dir_path, fwd=True, rev=True)
    return ReadsData(dir_path, fwd=True, rev=False)


def create_manifest(reads_data: ReadsData):
    fastq_path = os.path.join(reads_data.dir_path, "fastq")
    if not reads_data.rev:
        files = [os.path.join(fastq_path, f) for f in os.listdir(fastq_path)
                 if os.path.isfile(os.path.join(fastq_path, f))]
        names = [f.split('/')[-1].split('.')[0] for f in files]

        with open(os.path.join(reads_data.dir_path, 'manifest.tsv'), 'w') as manifest:
            tsv_writer = csv.writer(manifest, delimiter='\t')
            tsv_writer.writerow(["SampleID", "absolute-filepath"])
            for n, f in zip(*(names, files)):
                tsv_writer.writerow([n, f])
        return

    files_fwd = sorted([os.path.join(fastq_path, f) for f in os.listdir(fastq_path)
                        if os.path.isfile(os.path.join(fastq_path, f)) and "_1" in f])
    files_rev = sorted([os.path.join(fastq_path, f) for f in os.listdir(fastq_path)
                        if os.path.isfile(os.path.join(fastq_path, f)) and "_2" in f])
    names = sorted([f.split('.')[0] for f in os.path.join(reads_data.dir_path, "sra")])

    with open(os.path.join(reads_data.dir_path, 'manifest.tsv'), 'w') as manifest:
        tsv_writer = csv.writer(manifest, delimiter='\t')
        tsv_writer.writerow(["SampleID", "forward-absolute-filepath", "reverse-absolute-filepath"])
        for n, ff, fr in zip(*(names, files_fwd, files_rev)):
            tsv_writer.writerow([n, ff, fr])


def qiime_import(reads_data: ReadsData):
    run_cmd(["mkdir", os.path.join(reads_data.dir_path, "qza")])
    qza_path = os.path.join(reads_data.dir_path, "qza")
    paired = reads_data.rev and reads_data.fwd

    output_path = os.path.join(qza_path, f"demux-{'paired' if paired else 'single'}-end.qza")
    command = [
        "qiime", "tools", "import",
        "--type", f"'SampleData[{'PairedEndSequencesWithQuality' if paired else 'SequencesWithQuality'}]'",
        "--input-path", f"{os.path.join(reads_data.dir_path, 'manifest.tsv')}",
        "--input-format", "PairedEndFastqManifestPhred33V2" if paired else "SingleEndFastqManifestPhred33V2",
        "--output-path", output_path
    ]
    run_cmd(command)
    return output_path


def qiime_demux(reads_data: ReadsData, input_path: str, output_vis_path: str = ""):
    if output_vis_path == "":
        run_cmd(["mkdir", os.path.join(reads_data.dir_path, "vis")])
        output_path = os.path.join(reads_data.dir_path, "vis", os.path.split(input_path)[-1].split(".")[0] + ".qzv")
    else:
        output_path = output_vis_path

    command = [
        "qiime", "demux", "summarize",
        "--i-data", input_path,
        "--o-visualization", output_path
    ]
    run_cmd(command)
    return output_path


def visualization(*, acc_list, output_vis_path):
    check_conda_qiime2()

    start_import = datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    run_cmd(["mkdir", f"SRA-Importer-{start_import}"])
    dir_path = os.path.join(os.path.abspath("."), f"SRA-Importer-{start_import}")
    check_input(acc_list, output_vis_path)

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start prefetch (1/5)")
    download_data_from_sra(dir_path, acc_list)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish prefetch (1/5)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start converting .sra to .fastq (2/5)")
    reads_data = sra_to_fastq(dir_path)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish converting .sra to .fastq (2/5)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start creating manifest (3/5)")
    create_manifest(reads_data)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish creating manifest (3/5)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start 'qiime import' (4/5)")
    output_path = qiime_import(reads_data)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish 'qiime import' (4/5)")

    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Start 'qiime demux' (5/5)")
    vis_path = qiime_demux(reads_data, output_path, output_vis_path)
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish 'qiime demux' (5/5)")

    pickle.dump(reads_data, open(os.path.join(reads_data.dir_path, "reads_data.pkl"), "wb"))
    print(f"{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} -- Finish creating visualization\n")

    print(f"Visualization file is located in {vis_path}\n"
          f"Please drag this file to https://view.qiime2.org/ and continue.\n")
    if reads_data.fwd and reads_data.rev:
        print(f"Note: The data has both forward and reverse reads.\n"
              f"Therefore, you must give the parameters 'trim' and 'trunc' of export() "
              f"as a tuple of two integers."
              f"The first place related to the forward read and the second to the reverse.")
    else:
        print(f"Note: The data has only a forward read.\n"
              f"Therefore, you must give the parameters 'trim' and 'trunc' of export() "
              f"exactly one integers value which is related to the forward read.")

    return reads_data.dir_path
