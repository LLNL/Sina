#!/usr/bin/env python3

import argparse
import collections
import os
import subprocess
import sys
from pathlib import Path


Platform = collections.namedtuple(
    'Platform',
    ['name', 'host_config', 'toolchain_file'])


def build(platform: Platform, configure_only: bool) -> None:
    print('>>>> Building', platform.name)

    build_dir = f'build-{platform.name}'
    try:
        os.mkdir(build_dir)
    except FileExistsError as err:
        print(f'Directory {build_dir} already exists')
        return True

    host_config = Path('../CMake/host-configs') / platform.host_config
    toolchain_file = Path('../CMake/Platform') / platform.toolchain_file

    try:
        common_args = dict(
            cwd=build_dir,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        subprocess.run(['cmake',
                        '-C',
                        host_config,
                        f'-DCMAKE_TOOLCHAIN_FILE={toolchain_file}',
                        '..'],
                       **common_args)

        if not configure_only:
            subprocess.run(['make', '-j', 'all', 'test'],
                           **common_args)
    except subprocess.CalledProcessError as err:
        return True

    return False


def should_build(platform: Platform, args: argparse.ArgumentParser) -> bool:
    return (platform.name in args.platforms
            or not args.platforms)


def main() -> None:
    parser = argparse.ArgumentParser('Run the default builds')
    parser.add_argument('--configure-only', action='store_true', default=False,
                        help='Whether to only configure the build and not run it')
    parser.add_argument('platforms', type=str, nargs='*',
                        help='The platforms to build. If unspecified, all are built')
    args = parser.parse_args()

    all_platforms = [
        Platform(
            'intel',
            Path('sina-linux-rhel7-ivybridge-intel@classic-2021-6-0.cmake'),
            Path('toss_4_x86_64_intel.cmake')
        ),
        Platform(
            'clang',
            Path('sina-linux-rhel7-ivybridge-clang@14.0.6.cmake'),
            Path('toss_4_x86_64_clang.cmake')
        ),
        Platform(
            'gcc',
            Path('sina-linux-rhel7-ivybridge-gcc@10.2.1.cmake'),
            Path('toss_3_x86_64_gcc.cmake')
        ),
    ]

    got_error = False

    for platform in all_platforms:
        if should_build(platform, args):
            got_error |= build(platform, args.configure_only)

    all_platform_names = [p.name for p in all_platforms]
    for platform in args.platforms:
        if not platform in all_platform_names:
            print('Unrecognized platform:', platform, file=sys.stderr)
            got_error = True

    if got_error:
        print('Encountered build errors. See log above.', file=sys.stderr)

    return got_error


if __name__ == '__main__':
    sys.exit(int(main()))

