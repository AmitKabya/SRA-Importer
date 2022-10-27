from __future__ import annotations

import csv
import getopt
import os.path
import pickle
import datetime
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from chromedriver_py import binary_path

from .utilities import run_cmd, ReadsData, qiime2_version


def process_input(opts):
    """sra-study=", "acc-list=", "output-vis-path="""
    opts = dict(opts)

    if '--sra-study' not in opts and "--acc-list" not in opts:
        print("one of '--sra-study' or '--acc-list' must be given.")
        sys.exit(2)

    if '--sra-study' in opts and "--acc-list" in opts:
        print("one of '--sra-study' or '--acc-list' must be given. Cannot get both.")
        sys.exit(2)

    if '--acc-list' in opts:
        if not (os.path.exists(opts['--acc-list']) and os.path.isfile(opts['--acc-list'])):
            print("The given acc-list does not exist or is not a file.")
            sys.exit(2)
        acc_list = opts['--acc-list']
        sra_study = ""
    else:
        sra_study = opts['--sra-study']
        acc_list = ""

    if '--output-vis-path' not in opts:
        output_vis_path = ""
    else:
        t = os.path.join(*os.path.split(opts['--output-vis-path'])[:-1])
        if not (os.path.exists(t) and os.path.isdir(t) and opts['--output-vis-path'].split(".")[-1] == "qzv"):
            print("Invalid output-vis-path. output-vis-path must be a qzv file and be located in an existing directory."
                  "\noutput-vis-path will be saved in default location, under the created direction inside 'vis'")
            output_vis_path = ""
        else:
            output_vis_path = opts['--output-vis-path']

    return sra_study, acc_list, output_vis_path



def download_acc_list(dir_path: str, sra_study: str):
    """retrieve the Accession list from the sra website"""
    options = webdriver.ChromeOptions()
    options.add_argument(f"download.default_directory={dir_path}")
    options.add_argument(f"headless")

    service_object = Service(binary_path)
    driver = webdriver.Chrome(service=service_object, chrome_options=options)
    driver.get(f"https://www.ncbi.nlm.nih.gov/sra?term={sra_study}&cmd=DetailsSearch")

    driver.find_element(value="sendto").click()

    driver.find_element(value="dest_file").click()

    select = Select(driver.find_element(value='file_format'))
    select.select_by_value("acclist")

    driver.find_element(by=By.NAME,
                        value="EntrezSystem2.PEntrez.Sra.Sra_ResultsPanel.Sra_DisplayBar.SendToSubmit").click()


def download_data_from_sra(dir_path: str, sra_study: str = "", acc_list: str = ""):
    """
    return True if downloaded the data successfully, False O/W
    """
    run_cmd(["mkdir", os.path.join(dir_path, "sra")])
    if sra_study != "":
        download_acc_list(dir_path, sra_study)
        run_cmd(['prefetch', "--option-file", os.path.join(dir_path, "SraAccList.txt"), "--output-directory",
                 os.path.join(dir_path, "sra")])
        return
    run_cmd(['prefetch', "--option-file", acc_list, "--output-directory", os.path.join(dir_path, "sra")])


def sra_to_fastq(dir_path: str):
    run_cmd(["mkdir", os.path.join(dir_path, "fastq")])
    for sra_file in os.listdir(os.path.join(dir_path, "sra")):
        sra_path = os.path.join(dir_path, "sra", sra_file)
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


def conda_activate_qiime2():
    qiime_version = qiime2_version()
    run_cmd(["conda", "activate", qiime_version])


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


def main_importer():
    start_import = datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    run_cmd(["mkdir", f"SRA-Importer-{start_import}"])
    dir_path = os.path.join(os.path.abspath("."), f"SRA-Importer-{start_import}")

    def usage():
        print(f"usage: create_vis.py --sra-study <sra-study-code> --acc-list <accession-list-file-path> "
              f"--output-vis-path <final-output-path-of-visualisation>")

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", ["sra-study=", "acc-list=", "output-vis-path="])
        sra_study, acc_list, output_vis_path = process_input(opts)
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    download_data_from_sra(dir_path, sra_study, acc_list)

    reads_data = sra_to_fastq(dir_path)

    create_manifest(reads_data)

    conda_activate_qiime2()

    output_path = qiime_import(reads_data)

    vis_path = qiime_demux(reads_data, output_path, output_vis_path)

    pickle.dump(reads_data, open(os.path.join(reads_data.dir_path, "reads_data.pkl"), "wb"))

    print(f"Visualization file is located in {vis_path}\n"
          f"Please drag this file to https://view.qiime2.org/ and continue.\n")
    if reads_data.fwd and reads_data.rev:
        print(f"Note: The data has both forward and reverse reads.\n"
              f"Therefore, you must give the parameters '--trim' and '--trunc' of 'export.py' "
              f"two integers values seperated with a comma without space between. "
              f"The first place related to the forward read and the second to the reverse.\n"
              f"For example: export.py --trim 20,28 --trunc 200,200")
    else:
        print(f"Note: The data has only a forward read.\n"
              f"Therefore, you must give the parameters '--trim' and '--trunc' of 'export.py' "
              f"exactly one integers value which is related to the forward read.\n"
              f"For example: export.py --trim 20 --trunc 200")
