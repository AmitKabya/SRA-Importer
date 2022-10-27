import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ReadsData:
    dir_path: str
    fwd: bool = True
    rev: bool = False


def run_cmd(command: list):
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = proc.communicate()
    return o.decode("utf-8"), e.decode("utf-8")


def qiime2_version():
    o, e = run_cmd(["conda", "env", "list"])
    qiime_version = ""
    for env_1 in o:
        for env_2 in env_1.split("/"):
            if "qiime2" in env_2 and " " not in env_2:
                qiime_version = env_2
    return qiime_version
