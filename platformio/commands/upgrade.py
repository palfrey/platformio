# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys

import click
import requests

from platformio import VERSION, __version__, exception, util


@click.command(
    "upgrade", short_help="Upgrade PlatformIO to the latest version")
def cli():
    latest = get_latest_version()
    if __version__ == latest:
        return click.secho(
            "You're up-to-date!\nPlatformIO %s is currently the "
            "newest version available." % __version__,
            fg="green")
    else:
        click.secho("Please wait while upgrading PlatformIO ...", fg="yellow")

        to_develop = not all([c.isdigit() for c in latest if c != "."])
        cmds = (["pip", "install", "--upgrade",
                 "https://github.com/platformio/platformio/archive/develop.zip"
                 if to_develop else "platformio"], ["platformio", "--version"])

        cmd = None
        r = None
        try:
            for cmd in cmds:
                cmd = [os.path.normpath(sys.executable), "-m"] + cmd
                r = None
                r = util.exec_command(cmd)

                # try pip with disabled cache
                if r['returncode'] != 0 and cmd[2] == "pip":
                    cmd.insert(3, "--no-cache-dir")
                    r = util.exec_command(cmd)

                assert r['returncode'] == 0
            assert "version" in r['out']
            actual_version = r['out'].strip().split("version", 1)[1].strip()
            click.secho(
                "PlatformIO has been successfully upgraded to %s" %
                actual_version,
                fg="green")
            click.echo("Release notes: ", nl=False)
            click.secho(
                "http://docs.platformio.org/en/stable/history.html", fg="cyan")
        except Exception as e:  # pylint: disable=W0703
            if not r:
                raise exception.UpgradeError("\n".join([str(cmd), str(e)]))
            permission_errors = ("permission denied", "not permitted")
            if (any([m in r['err'].lower() for m in permission_errors]) and
                    "windows" not in util.get_systype()):
                click.secho(
                    """
-----------------
Permission denied
-----------------
You need the `sudo` permission to install Python packages. Try

> sudo pip install -U platformio

WARNING! Don't use `sudo` for the rest PlatformIO commands.
""",
                    fg="yellow",
                    err=True)
                raise exception.ReturnErrorCode()
            else:
                raise exception.UpgradeError("\n".join([str(cmd), r['out'], r[
                    'err']]))


def get_latest_version():
    try:
        if not isinstance(VERSION[2], int):
            try:
                return get_develop_latest_version()
            except:  # pylint: disable=bare-except
                pass
        return get_pypi_latest_version()
    except:
        raise exception.GetLatestVersionError()


def get_develop_latest_version():
    version = None
    r = requests.get("https://raw.githubusercontent.com/platformio/platformio"
                     "/develop/platformio/__init__.py",
                     headers=util.get_request_defheaders())
    r.raise_for_status()
    for line in r.text.split("\n"):
        line = line.strip()
        if not line.startswith("VERSION"):
            continue
        match = re.match(r"VERSION\s*=\s*\(([^\)]+)\)", line)
        if not match:
            continue
        version = match.group(1)
        for c in (" ", "'", '"'):
            version = version.replace(c, "")
        version = ".".join(version.split(","))
    assert version
    return version


def get_pypi_latest_version():
    r = requests.get("https://pypi.python.org/pypi/platformio/json",
                     headers=util.get_request_defheaders())
    r.raise_for_status()
    return r.json()['info']['version']
