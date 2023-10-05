#!/usr/bin/env python3

######################################################
# TUbe-dl
# Utility to download all video items from TUbe (https://portal.tuwien.tv/)
#
# Author: Kippi
# Version: 0.0.1
######################################################


import argparse
import os
import requests
import shutil
import sys

from pyquery import PyQuery
from string import Template
from urllib.parse import urlparse


CHUNK_SIZE = 64*1024
PROGRESS_SIGN = '#'
NO_PROGRESS_SIGN = '-'


def resume_download(fileurl, resume_byte_pos, headers=None):
    if headers is None:
        headers = {}
    headers['Range'] = f'bytes={resume_byte_pos}-'
    return requests.get(fileurl, headers=headers, stream=True, timeout=10)


def main():
    if sys.version_info < (3, 6):
        sys.stderr.write('You need Python 3.6 or later\n')
        sys.exit(1)

    # Tolerate 32 spaces until the description is put a line below
    def more_indent_formatter(prog): return argparse.RawTextHelpFormatter(prog, max_help_position=32)
    parser = argparse.ArgumentParser(description='Download add video items from TUbe', formatter_class=more_indent_formatter)
    parser.add_argument('-c',
                        '--cookie',
                        type=str,
                        action='store',
                        dest='cookie',
                        required=True,
                        help='The cookie header')
    parser.add_argument('-f',
                        '--force',
                        action='store_true',
                        dest='force',
                        required=False,
                        default=False,
                        help='Overwrite or append already existing files without confirmation')
    parser.add_argument('-o',
                        '--out',
                        type=str,
                        action='store',
                        dest='dir',
                        required=True,
                        help='The directory to put the videos in. It will be created if it does not exist')
    parser.add_argument('-q',
                        '--quiet',
                        action='store_true',
                        dest='quiet',
                        required=False,
                        default=False,
                        help='Be quiet and do not print progress')
    parser.add_argument('-u',
                        '--url',
                        type=str,
                        action='store',
                        dest='url',
                        required=True,
                        help='The address of the video items')

    # Set all arguments
    args = parser.parse_args()
    cookie = args.cookie
    force = args.force
    outdir = args.dir
    quiet = args.quiet
    url = args.url

    # Fetch the website
    r = requests.get(url, headers={'Cookie': cookie}, timeout=10)
    r.encoding = 'utf-8'
    if r.status_code != requests.codes.ALL_OKAY:
        sys.stderr.write(f'Error fetching content from "{url}"')
        sys.exit(1)

    videos = PyQuery(r.text)('#div_PLItemsList-Tour')

    # Create any parent directories if necessary
    os.makedirs(outdir, exist_ok=True)

    # Get terminal size and compute name and progress areas sizes
    termwidth = shutil.get_terminal_size()[0]
    name_size = progarea_size = int(termwidth/2 - 1)
    space_count = 2 + termwidth % 2

    # Parse url for easy creation of full_vidurl
    url_parts = urlparse(url)

    for video in videos.items('.playlist'):
        vidurl = video.attr['data-vidurl']
        name = video.find('.title').text()

        # Make vidurl absolute and complete
        vidurl_parts = urlparse(vidurl)
        if vidurl_parts.netloc == '':
            # Absolute path
            if vidurl[0] == '/':
                vidurl = f'{url_parts.scheme}://{url_parts.netloc}{vidurl}'
            # Relative path
            else:
                # Get the directory to append the relative path to by discarding everything after the last /
                url_dir = url[:url.rfind('/')]
                vidurl = f'{url_dir}/{vidurl}'
        else:
            # Handle //example.org/123 case
            if vidurl_parts.scheme == '':
                vidurl = f'https:{vidurl}'
            # else: vidurl = vidurl

        filename = os.path.join(outdir, f'{name}.mp4')
        filemode = 'ab'

        # Get position for resuming the download
        try:
            position = os.path.getsize(filename)
        except FileNotFoundError:
            position = 0
            filemode = 'wb'

        with resume_download(vidurl, position, headers={'Cookie': cookie}) as r:
            if len(name) - 3 > name_size:
                # Truncate name to name_size
                name_template = f'{name[:name_size-3]}...'
            else:
                # Fill name with spaces to name_size
                name_template = name + ' ' * (name_size - len(name))

            if r.status_code == requests.codes.RANGE_NOT_SATISFIABLE:
                print(f'{name_template}{" " * space_count}Already downloaded')
                continue
            elif r.status_code < 200 or r.status_code > 299:
                print(f'Error downloading "{name}": {r.reason}')
                continue

            content_size = r.headers.get('Content-Length')
            downloaded = 0

            if r.headers.get('Accept-Ranges') in [None, 'none']:
                # Overwrite the file if ranges are not supported
                filemode = 'wb'

                if not force:
                    resp = input(f'Server does not support resumeable downloads, download whole file again? [y/N]: ').upper()
                    if resp not in ['Y', 'YES']:
                        continue

            if len(name) - 3 > name_size:
                # Truncate name to name_size
                name_template = f'{name[:name_size-3]}...'
            else:
                # Fill name with spaces to name_size
                name_template = name + ' ' * (name_size - len(name))

            progress_template = Template(f'{name_template}{" " * space_count}[$progress] $percent%')
            max_progress = progarea_size - 7    # The maximum number of PROGRESS_SIGNs to print
            def print_progress(progress):
                nonlocal progress_template, max_progress

                percent = f'{int(progress * 100):>3d}'

                # Print a number of PROGRESS_SIGNs relative to the progress made and fill the rest up with NO_PROGRESS_SIGN
                progress_string = int(max_progress * progress) * PROGRESS_SIGN
                progress_string += NO_PROGRESS_SIGN * (max_progress - len(progress_string))

                sys.stdout.write(f'\r{progress_template.substitute(progress=progress_string, percent=percent)}')
                sys.stdout.flush()

            # Do not display progress bar if we cannot calculate the progress, print static content instead
            if content_size is None:
                if not quiet:
                    print(f'Downloading "{name}"...')
            else:
                content_size = int(content_size)
                print_progress(downloaded / content_size)

            with open(filename, filemode) as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Display progress bar only if we can calculate progress
                    if content_size is not None and not quiet:
                        print_progress(downloaded / content_size)


if __name__ == '__main__':
    main()
