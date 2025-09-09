import json
import re
import shlex
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
import os

origGetAddrInfo = socket.getaddrinfo


def getAddrInfoWrapper(host, port, family=0, socktype=0, proto=0, flags=0):
    return origGetAddrInfo(host, port, socket.AF_INET, socktype, proto, flags)


# Force ipv4 usege to avoid urllib getting stuck on requests
# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = getAddrInfoWrapper


def date_from_burst(burst_path):
    return Path(burst_path).parent.name.split("_")[2]


def parse_date(date_str: str) -> datetime:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return datetime.strptime(date_str, "%Y-%m-%d")
    if re.match(r"^\d{4}\d{2}\d{2}$", date_str):
        return datetime.strptime(date_str, "%Y%m%d")
    try:
        return datetime.strptime(date_str, "%Y%m%dT%H%M%S")
    except ValueError:
        pass
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def union_aabbox(a: list, b: list) -> list:
    """
    Union of two axis-aligned bounding boxes (AABBs).
    """
    return [
        min(a[0], b[0]),
        min(a[1], b[1]),
        max(a[2], b[2]),
        max(a[3], b[3]),
    ]


def parse_json_from_output(output_str: str) -> Dict[str, Any]:
    lines = output_str.split("\n")
    parsing_json = False
    json_str = ""
    # reverse order to get last possible json line
    for l in reversed(lines):
        if not parsing_json:
            if l.endswith("}"):
                parsing_json = True
        json_str = l + json_str
        if l.startswith("{"):
            break

    return json.loads(json_str)


def merge_two_dicts(x, y):
    z = x.copy()  # start with keys and values of x
    z.update(y)  # modifies z with keys and values of y
    return z


def exec_proc(command, cwd=None, write_output=True, env=None):
    if isinstance(command, str):
        command_to_display = command
        command_list = shlex.split(command)
    else:
        command = list(map(lambda x: str(x), command))
        command_to_display = subprocess.list2cmdline(command)
        command_list = command
    if cwd is None:
        cwd = os.getcwd()
    elif not os.path.exists(cwd):
        raise Exception("cwd does not exist: " + str(cwd))

    if env is None:
        env = {}

    keys_values = env.items()
    # convert all values to strings:
    env = {str(key): str(value) for key, value in keys_values}
    new_env = merge_two_dicts(os.environ, env)

    # print commands that can be pasted in the console
    print(f'> cwd "{cwd}"')
    for key in env:
        print(key + "=" + str(subprocess.list2cmdline([env[key], ""])[:-3]))
    print("" + command_to_display)

    try:
        output = ""
        process = subprocess.Popen(
            command_list,
            cwd=cwd,
            universal_newlines=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            env=new_env,
        )

        with process:
            for line in process.stdout:
                if write_output:
                    sys.stdout.write(line)
                output += line
            ret = process.wait()

    except subprocess.CalledProcessError as ex:
        ret = ex.returncode
        output = ex.output

    if ret != 0:
        if not write_output:
            print(output)
        raise Exception("Process returned error status code: " + str(ret), ret, output)
    return ret, output
