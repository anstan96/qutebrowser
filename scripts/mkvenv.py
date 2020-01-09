#!/usr/bin/env python3
# vim: ft=python fileencoding=utf-8 sts=4 sw=4 et:

# Copyright 2020 Florian Bruhin (The Compiler) <mail@qutebrowser.org>

# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.


"""Create a local virtualenv with a PyQt install."""

import argparse
import pathlib
import sys
import os
import os.path
import typing
import shutil
import venv
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from scripts import utils, link_pyqt


REPO_ROOT = pathlib.Path(__file__).parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keep',
                        action='store_true',
                        help="Reuse an existing virtualenv.")
    parser.add_argument('--venv-dir',
                        default='.venv',
                        help="Where to place the virtualenv.")
    parser.add_argument('--pyqt-version',
                        choices=pyqt_versions(),
                        default='auto',
                        help="PyQt version to install")
    parser.add_argument('--pyqt-type',
                        choices=['binary', 'source', 'link'],
                        default='binary',
                        help="How to install PyQt/Qt.")
    parser.add_argument('--tox-error',
                        action='store_true',
                        help=argparse.SUPPRESS)
    return parser.parse_args()


def pyqt_versions() -> typing.List[str]:
    version_set = set()

    requirements_dir = REPO_ROOT / 'misc' / 'requirements'
    for req in requirements_dir.glob('requirements-pyqt-*.txt'):
        version_set.add(req.stem.split('-')[-1])

    versions = sorted(version_set,
                      key=lambda v: [int(c) for c in v.split('.')])
    return versions + ['auto']


def run_venv(venv_dir: pathlib.Path, executable, *args: str) -> None:
    subdir = 'Scripts' if os.name == 'nt' else 'bin'

    try:
        subprocess.run([str(venv_dir / subdir / executable)] +
                       [str(arg) for arg in args], check=True)
    except subprocess.CalledProcessError as e:
        utils.print_col("Subprocess failed, exiting", 'red')
        sys.exit(e.returncode)


def pip_install(venv_dir: pathlib.Path, *args: str) -> None:
    arg_str = ' '.join(str(arg) for arg in args)
    utils.print_col('venv$ pip install {}'.format(arg_str), 'blue')
    run_venv(venv_dir, 'python3', '-m', 'pip', 'install', *args)


def show_tox_error(pyqt_type: str) -> None:
    if pyqt_type == 'link':
        env = 'mkvenv'
        args = ' --pyqt-type link'
    elif pyqt_type == 'binary':
        env = 'mkvenv-pypi'
        args = ''
    else:
        raise AssertionError

    print()
    utils.print_col('tox -e {} is deprecated. Please use scripts/mkvenv.py{} '
                    'instead.'.format(env, args), 'red')
    print()


def delete_old_venv(venv_dir: pathlib.Path) -> None:
    if venv_dir.exists():
        utils.print_col('$ rm -r {}'.format(venv_dir), 'blue')
        shutil.rmtree(str(venv_dir))


def create_venv(venv_dir: pathlib.Path) -> None:
    utils.print_col('$ python3 -m venv {}'.format(venv_dir), 'blue')
    venv.create(str(venv_dir), with_pip=True)


def upgrade_pip(venv_dir: pathlib.Path) -> None:
    utils.print_title("Upgrading pip")
    pip_install(venv_dir, '-U', 'pip')


def pyqt_requirements_file(version: str):
    suffix = '' if version == 'auto' else '-{}'.format(version)
    return (REPO_ROOT / 'misc' / 'requirements' /
            'requirements-pyqt{}.txt'.format(suffix))


def install_pyqt_binary(venv_dir: pathlib.Path, version: str) -> None:
    utils.print_title("Installing PyQt from binary")
    utils.print_col("No proprietary codec support will be available in "
                    "qutebrowser.", 'red')
    pip_install(venv_dir, '-r', pyqt_requirements_file(version),
                '--only-binary', 'PyQt5,PyQtWebEngine')


def install_pyqt_source(venv_dir: pathlib.Path, version: str) -> None:
    utils.print_title("Installing PyQt from sources")
    pip_install(venv_dir, '-r', pyqt_requirements_file(version),
                '--verbose', '--no-binary', 'PyQt5,PyQtWebEngine')


def install_pyqt_link(venv_dir: pathlib.Path) -> None:
    utils.print_title("Linking system-wide PyQt")
    lib_path = link_pyqt.get_venv_lib_path(str(venv_dir))
    link_pyqt.link_pyqt(sys.executable, lib_path)


def install_requirements(venv_dir: pathlib.Path) -> None:
    utils.print_title("Installing other qutebrowser dependencies")
    requirements_file = REPO_ROOT / 'requirements.txt'
    pip_install(venv_dir, '-r', str(requirements_file))


def install_qutebrowser(venv_dir: pathlib.Path) -> None:
    utils.print_title("Installing qutebrowser")
    pip_install(venv_dir, '-e', str(REPO_ROOT))


def main() -> None:
    args = parse_args()
    venv_dir = pathlib.Path(args.venv_dir)
    utils.change_cwd()

    if args.tox_error:
        show_tox_error(args.pyqt_type)
        sys.exit(1)

    if not args.keep:
        utils.print_title("Creating virtual environment")
        delete_old_venv(venv_dir)
        create_venv(venv_dir)

    upgrade_pip(venv_dir)

    if args.pyqt_type == 'binary':
        install_pyqt_binary(venv_dir, args.pyqt_version)
    elif args.pyqt_type == 'source':
        install_pyqt_source(venv_dir, args.pyqt_version)
    elif args.pyqt_type == 'link':
        install_pyqt_link(venv_dir)
    else:
        raise AssertionError

    install_requirements(venv_dir)
    install_qutebrowser(venv_dir)


if __name__ == '__main__':
    main()
