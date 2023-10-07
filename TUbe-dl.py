#!/usr/bin/env python3

######################################################
# TUbe-dl
# Utility to download a playlist from TUbe (https://portal.tuwien.tv/)
#
# Author: Kippi
# Version: 0.0.2
######################################################


import argparse
import os
import requests
import shutil
import sys
import threading

from pyquery import PyQuery
from string import Template
from urllib.parse import urlparse


CHUNK_SIZE = 64*1024


class RepeatTimer(threading.Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class ProgressFormatter:
    PROGRESS_TEMPLATE = Template(f'[$progress] $percent%')
    PROGRESS_SIGN = '#'
    NO_PROGRESS_SIGN = '-'

    def __init__(self, name):
        # Get terminal size and compute name and progress areas sizes
        termwidth = shutil.get_terminal_size()[0]
        self._name_size = self._progarea_size = int(termwidth/2 - 1)

        # The maximum number of PROGRESS_SIGNs to print
        self._max_progress = self._progarea_size - 7

        # For symmetry's sake print 3 spaces when termwidth is odd and two if it is even
        self._spaces = ' ' * (2 + termwidth % 2)

        self.name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if len(value) - 3 > self._name_size:
            # Truncate name to name_size
            self._name = f'{value[:self._name_size-3]}...'
        else:
            # Fill name with spaces to name_size
            self._name = value + ' ' * (self._name_size - len(value))

    def format_progress(self, progress):
        percent = f'{int(progress * 100):>3d}'

        # Print a number of PROGRESS_SIGNs relative to the progress made and fill the rest up with NO_PROGRESS_SIGN
        progress_bar = int(self._max_progress * progress) * self.PROGRESS_SIGN
        progress_bar += self.NO_PROGRESS_SIGN * (self._max_progress - len(progress_bar))

        progress_string = self.PROGRESS_TEMPLATE.substitute(progress=progress_bar, percent=percent)

        return f'{self.name}{self._spaces}{progress_string}'

    def format_msg(self, msg):
        return f'{self.name}{self._spaces}{msg}'


def resume_download(fileurl, resume_byte_pos, headers=None):
    if headers is None:
        headers = {}
    headers['Range'] = f'bytes={resume_byte_pos}-'
    return requests.get(fileurl, headers=headers, stream=True, timeout=10)


def download_video(vidurl, filename, cookie, prog_formatter, force=False, quiet=False):
    filemode = 'ab'

    # Get position for resuming the download
    try:
        position = os.path.getsize(filename)
    except FileNotFoundError:
        position = 0
        filemode = 'wb'

    with resume_download(vidurl, position, headers={'Cookie': cookie}) as r:
        if r.status_code == requests.codes.RANGE_NOT_SATISFIABLE:
            if not quiet:
                print(prog_formatter.format_msg('Already downloaded'))
            return
        else:
            r.raise_for_status()

        if r.headers.get('Accept-Ranges') in [None, 'none']:
            # Overwrite the file if ranges are not supported
            filemode = 'wb'

            if not force:
                resp = input(f'Server does not support resumeable downloads, download whole file again? [y/N]: ').upper()
                if resp not in ['Y', 'YES']:
                    return

        content_size = r.headers.get('Content-Length')
        downloaded = 0
        def print_progress():
            nonlocal prog_formatter, content_size, downloaded

            sys.stdout.write(f'\r{prog_formatter.format_progress(downloaded / content_size)}')
            sys.stdout.flush()

        # Print progress every 0.5s
        print_progress_timer = RepeatTimer(0.5, print_progress)

        # Stop print_progress_timer on CTRL+C
        print_progress_timer.daemon = True

        # Do not display progress bar if we cannot calculate the progress, print static content instead
        if not quiet:
            if content_size is None:
                print(prog_formatter.format_msg('Downloading...'))
            else:
                content_size = int(content_size)
                print_progress()
                print_progress_timer.start()

        with open(filename, filemode) as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                downloaded += CHUNK_SIZE

        if not quiet:
            # Stop printing the progress
            print_progress_timer.cancel()

            # Since content_size is not always a multiple of CHUNK_SIZE, align the two to avoid having >100% progress
            downloaded = content_size

            # Print the progress one last time to override any potential >100% progress output
            print_progress()

            # Terminate the line to avoid overwriting
            sys.stdout.write('\n')


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
        try:
            download_video(vidurl, filename, cookie, ProgressFormatter(name), force, quiet)
        except Exception as e:
            sys.stderr.write(f'Error downloading "{name}": {e}\n')


if __name__ == '__main__':
    main()
