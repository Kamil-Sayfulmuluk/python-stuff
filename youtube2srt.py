import re
import sys
import logging
import os

from dataclasses import dataclass, field
from functools import reduce
from os.path import exists, isfile
from typing import List, Any

PARAMS_COUNT = 2  # python [script_name(0), src_filename.txt(1)]
CMD_INDEX = 0
FIRST_PARAM_INDEX = 1
ITEMS_IN_TIME_RANK = 60
LAST_TIME_DURATION = 5  # in seconds
MAX_TIME_RANKS = 3
MIN_TIME_RANKS = 2


@dataclass
class SubtitleItem:
    from_time: List[Any] = field(default_factory=list)
    till_time: List[Any] = field(default_factory=list)
    text: str = ''


class BadSourceFileError(Exception):
    def __init__(self):
        super().__init__('Source subtitles file is of wrong format.')


def get_formatted_time_line(time_line: list = []):
    return reduce(
        lambda a, b: (f'{a:02}' if isinstance(a, int) else a) + f':{b:02}',
        time_line,
    )


def get_filename_with_new_extension(filename, new_extension="srt"):
    filename_without_extension = re.sub(r'\..*$', '', filename)
    return f"{filename_without_extension}.{new_extension}"


def get_src_files():
    if len(sys.argv) < PARAMS_COUNT:
        sys.exit("ERROR: Wrong params count. Use like this: python youtube2srt.py src_file.txt")
    return sys.argv[1:]


def get_time_line(s):
    """
    Allowed s value: [59:]59:59
    Returning value: [i1, i2, i3]
    """
    if not (res := re.search(r'[\d:]+', s)):
        return []
    res = res.group(0)
    try:
        time_line = [int(x) for x in res.split(':') if (len(x) <= 2 and int(x) < ITEMS_IN_TIME_RANK) or 1/0]
        return [
            *([0] * (MAX_TIME_RANKS - len(time_line))), *time_line,
        ] if (MIN_TIME_RANKS <= len(time_line) <= MAX_TIME_RANKS) else []
    except ZeroDivisionError:
        return []


def get_without_eols(line):
    return re.sub('[\n\r]+', '', line)


def get_youtube_subtitles(filename):
    with open(filename, 'rt') as f:
        subtitle = None
        subtitles = []
        time_line_not_found = time_line_is_next = True
        while (s := f.readline()):
            s = get_without_eols(s)
            if not s.strip() and time_line_not_found:
                continue
            if time_line_is_next:
                if not (time_line := get_time_line(s)):
                    raise BadSourceFileError()
                subtitle = SubtitleItem(
                    from_time=time_line,
                    till_time=[],
                )
                if subtitles:
                    subtitles[-1].till_time = subtitle.from_time.copy()
                subtitles.append(subtitle)
            else:
                subtitle.text = s
            time_line_is_next = not time_line_is_next
        else:
            if subtitles:
                subtitles[-1].till_time = subtitles[-1].from_time.copy()
                subtitles[-1].till_time[-1] += LAST_TIME_DURATION
    return subtitles


def write_subtitles_to_srt_file(subtitles, srt_filename):
    with open(srt_filename, 'wt') as f:
        for i, subtitle in enumerate(subtitles):
            f.write(f'{i+1}\n')
            f.write(
                "{},000 --> {},000\n".format(
                    get_formatted_time_line(subtitle.from_time),
                    get_formatted_time_line(subtitle.till_time),
                )
            )
            f.write(f'{subtitle.text}\n\n')


def execute_converting_process(filename, log=logging.getLogger(__name__)):
    if not isfile(filename):
        return
    try:
        subtitles = get_youtube_subtitles(filename)
    except BadSourceFileError:
        log.error(f"Bad subtitles source file error: {filename}\n")
        return
    dst_filename = get_filename_with_new_extension(filename)
    if exists(dst_filename):
        response = input(f'The destination file {dst_filename} already exists. \nDo you want to proceed?(y/n)')
        if response.strip().lower() != 'y':
            log.info(f'{dst_filename} was kept unchanged')
            return
    write_subtitles_to_srt_file(subtitles, dst_filename)
    log.info(f'{dst_filename} ok')


if __name__ == "__main__":
    """
    Converts youtube transcript file to .srt format (compatible with VLC-player)
    Using:
        python youtube2srt.py youtube_transcript_file_name.txt
    """
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    log = logging.getLogger(__name__)
    for filename in get_src_files():
        execute_converting_process(filename, log)
