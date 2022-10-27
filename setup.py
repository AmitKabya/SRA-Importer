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
    if os.path.exists(o.decode('utf-8').strip()) and e == b'':
        return True
    return False


def has_qiime2_conda_env():
    proc = subprocess.Popen(["conda", "env", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = proc.communicate()
    o, e = o.decode("utf-8"), e.decode("utf-8")
    qiime_version = ""
    for env_1 in o:
        for env_2 in env_1.split("/"):
            if "qiime2" in env_2 and " " not in env_2:
                qiime_version = env_2
    return qiime_version != ""


if __name__ == '__main__':

    if not has_qiime2_conda_env():
        raise Exception("Could not find an existing qiime2 conda environment on this machine.\n"
                        "Download a qiime2 conda environment and then try again")

    if not sra_toolkit_installed():
        raise Exception("Could not find an installed sra-toolkit on this machine.\n"
                        "Download an sra-toolkit and then try again.")
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
        install_requires=requirements,
        packages=find_packages('SRA'),
        python_requires=">=3.6.8",
        include_package_data=True,
        has_ext_modules=lambda: True,
        package_dir={"": "SRA"},
        classifiers=[
            'Programming Language :: Python',
            'Operating System :: Unix',
            'Operating System :: POSIX :: Linux',
        ],
        easy_install="ok_zip"
    )
