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

import json

import click

from platformio import app, exception, util
from platformio.managers.platform import PlatformFactory, PlatformManager


@click.group(short_help="Platform Manager")
def cli():
    pass


def _print_platforms(platforms):
    for platform in platforms:
        click.echo("{name} ~ {title}".format(
            name=click.style(
                platform['name'], fg="cyan"),
            title=platform['title']))
        click.echo("=" * (3 + len(platform['name'] + platform['title'])))
        click.echo(platform['description'])
        click.echo()
        click.echo("Home: %s" % "http://platformio.org/platforms/" + platform[
            'name'])
        if platform['packages']:
            click.echo("Packages: %s" % ", ".join(platform['packages']))
        if "version" in platform:
            click.echo("Version: " + platform['version'])
        click.echo()


@cli.command("search", short_help="Search for development platforms")
@click.argument("query", required=False)
@click.option("--json-output", is_flag=True)
def platform_search(query, json_output):
    platforms = []
    for platform in util.get_api_result("/platforms"):
        if query == "all":
            query = ""

        search_data = json.dumps(platform)
        if query and query.lower() not in search_data.lower():
            continue

        # @TODO update API with NAME/TITLE
        platforms.append({
            "name": platform['type'],
            "title": platform['name'],
            "description": platform['description'],
            "packages": platform['packages']
        })

    if json_output:
        click.echo(json.dumps(platforms))
    else:
        _print_platforms(platforms)


@cli.command("install", short_help="Install new platforms")
@click.argument("platforms", nargs=-1, required=True, metavar="[PLATFORM...]")
@click.option("--with-package", multiple=True)
@click.option("--without-package", multiple=True)
@click.option("--skip-default-package", is_flag=True)
def platform_install(platforms, with_package, without_package,
                     skip_default_package):
    pm = PlatformManager()
    for platform in platforms:
        if pm.install(
                name=platform,
                with_packages=with_package,
                without_packages=without_package,
                skip_default_package=skip_default_package):
            click.secho(
                "The platform '%s' has been successfully installed!\n"
                "The rest of packages will be installed automatically "
                "depending on your build environment." % platform,
                fg="green")


@cli.command("uninstall", short_help="Uninstall platforms")
@click.argument("platforms", nargs=-1, required=True, metavar="[PLATFORM...]")
def platform_uninstall(platforms):
    pm = PlatformManager()
    for platform in platforms:
        if pm.uninstall(platform):
            click.secho(
                "The platform '%s' has been successfully "
                "uninstalled!" % platform,
                fg="green")


@cli.command("update", short_help="Update installed Platforms")
@click.argument("platforms", nargs=-1, required=False, metavar="[PLATFORM...]")
@click.option(
    "-p",
    "--only-packages",
    is_flag=True,
    help="Update only platform packages")
@click.option(
    "-c",
    "--only-check",
    is_flag=True,
    help="Do not update, only check for new version")
def platform_update(platforms, only_packages, only_check):
    pm = PlatformManager()
    if not platforms:
        platforms = set([m['name'] for m in pm.get_installed()])
    for platform in platforms:
        click.echo("Platform %s" % click.style(platform, fg="cyan"))
        click.echo("--------")
        pm.update(platform, only_packages=only_packages, only_check=only_check)
        click.echo()


@cli.command("list", short_help="List installed platforms")
@click.option("--json-output", is_flag=True)
def platform_list(json_output):
    platforms = []
    pm = PlatformManager()
    for manifest in pm.get_installed():
        p = PlatformFactory.newPlatform(
            pm.get_manifest_path(manifest['__pkg_dir']))
        platforms.append({
            "name": p.name,
            "title": p.title,
            "description": p.description,
            "version": p.version,
            "packages": p.get_installed_packages().keys()
        })

    if json_output:
        click.echo(json.dumps(platforms))
    else:
        _print_platforms(platforms)


@cli.command("show", short_help="Show details about installed Platform")
@click.argument("platform")
@click.pass_context
def platform_show(ctx, platform):
    try:
        p = PlatformFactory.newPlatform(platform)
    except exception.UnknownPlatform:
        if (not app.get_setting("enable_prompts") or
                click.confirm("The platform '%s' has not been installed yet. "
                              "Would you like to install it now?" % platform)):
            ctx.invoke(platform_install, platforms=[platform])
        else:
            raise exception.PlatformNotInstalledYet(platform)

    click.echo("{name} ~ {title}".format(
        name=click.style(
            p.name, fg="cyan"), title=p.title))
    click.echo("=" * (3 + len(p.name + p.title)))
    click.echo(p.description)
    click.echo()
    click.echo("Version: %s" % p.version)
    if p.homepage:
        click.echo("Home: %s" % p.homepage)
    if p.license:
        click.echo("License: %s" % p.license.get("type"))
    if p.frameworks:
        click.echo("Frameworks: %s" % ", ".join(p.frameworks.keys()))

    if not p.packages:
        return

    installed_pkgs = p.get_installed_packages()
    for name, opts in p.packages.items():
        click.echo()
        click.echo("Package %s" % click.style(name, fg="yellow"))
        click.echo("-" * (8 + len(name)))
        if p.get_package_type(name):
            click.echo("Type: %s" % p.get_package_type(name))
        click.echo("Requirements: %s" % opts.get("version"))
        click.echo("Installed: %s" % ("Yes" if name in installed_pkgs else
                                      "No (optional)"))
        if name in installed_pkgs:
            for key, value in installed_pkgs[name].items():
                if key in ("url", "version", "description"):
                    click.echo("%s: %s" % (key.title(), value))
