import os.path
import subprocess

from setuptools import setup, find_packages


def sra_toolkit_installed():
    """
    check if sra-toolkit is downloaded on the machine
    """
    cmd = ['which', 'fastq-dump']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    o, e = proc.communicate()
    o, e = o.decode("utf-8"), e.decode("utf-8")
    return os.path.exists(o.strip()) and e == ''


def has_qiime2_conda_env():
    proc = subprocess.Popen(["conda", "env", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = proc.communicate()
    o, e = o.decode("utf-8"), e.decode("utf-8")
    return "qiime2" in o


if __name__ == '__main__':

    # check requirements on a linux + conda machine
    # assuming that machine that uses conda is a linux machine
    conda_prefix = os.environ.get("CONDA_PREFIX", None)
    if conda_prefix is not None:
        if not has_qiime2_conda_env():
            raise Exception("Could not find an existing qiime2 conda environment on this machine.\n"
                            "Download a qiime2 conda environment and then try again")

        if not sra_toolkit_installed():
            raise Exception("Could not find an installed sra-toolkit on this machine.\n"
                            "Download an sra-toolkit and then try again.")
    # continue installation on Windows just to be able to upload to pypi

    # get text for setup
    with open("requirements.txt") as f:
        requirements = [l.strip() for l in f.readlines()]

    with open("README.md") as r:
        readme = r.read()

    setup(
        name="SRA-Importer",
        version="0.0.1",
        license="MIT",
        maintainer="Amit Kabya",
        author="Amit Kabya",
        maintainer_email="kabya.amit@gmail.com",
        url="https://github.com/AmitKabya/SRA-Importer",
        description="An easy and convenient way to import data "
                    "from the sra database and creating OTU and Taxonomy tables.",
        long_description=readme,
        long_description_content_type="text/markdown",
        keywords=["sra", "bioinformatics", "taxonomy"],
        description_file="README.md",
        license_files="LICENSE.rst",
        install_requires=['subprocess', 'setuptools'],
        scripts=['bin/create-visualization',
                 'bin/export-data'],
        packages=find_packages('SRA-Importer'),
        python_requires=">=3.6.8",
        include_package_data=True,
        has_ext_modules=lambda: True,
        package_dir={"": "SRA-Importer"},
        classifiers=[
            'Programming Language :: Python',
            'Operating System :: Unix',
            'Operating System :: POSIX :: Linux',
        ],
        easy_install="ok_zip"
    )
