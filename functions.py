import json
import logging
import math
import os
import re
import sys
import time
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import List, Tuple, Dict, Optional

import bitstring
import imdb  # noqa
import magic
import mutagen
import requests
from imdb import IMDbDataAccessError
from mutagen.flac import VCFLACDict  # noqa
from mutagen.id3 import ID3
from pymediainfo import MediaInfo
from requests import Response
from termcolor import cprint

from config import whitelist_video_extensions, blacklist_media_extensions, whitelist_audio_extensions, \
    requests_retry_interval


class ValidationError(Exception):
    """Raised by plugins when incomplete or invalid files or metadata is passed in"""
    def __init__(self, errors: List[str]):
        self.errors = errors


class ConflictError(Exception):
    """Raised by plugins when the operation was skipped (e.g. during a duplicate upload attempt)"""
    def __init__(self, message: str, params: Dict[str, str] = None):
        self.message = message
        self.params = params


class PluginError(Exception):
    def __init__(self, err: str):
        self.error = err


class ServerError(Exception):
    def __init__(self, err: str):
        self.error = err


class UpdateError(Exception):
    def __init__(self, err: str):
        self.error = err


class MagicError(Exception):
    def __init__(self, err: str):
        self.error = err


class BulkMode(Enum):
    STANDARD = 1
    MUSIC = 2


folder_default = 'Select a folder to hash'


def error(msg):
    try:
        decoded = json.loads(msg)
        if 'errors' in decoded:
            if len(decoded['errors']) > 1:
                cprint("Error:", 'red')
                for err in decoded['errors']:
                    cprint(err, 'red')
            else:
                cprint("Error: {0}".format(decoded['errors'][0]), 'red')

    except ValueError:
        cprint(msg, 'red')

    sys.exit(1)


def requests_retriable_post(url: str, **kwargs) -> Response:
    while True:
        try:
            response = requests.post(url, **kwargs)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            cprint("Connection error, retrying...", 'red')
            time.sleep(requests_retry_interval)
        except requests.exceptions.RequestException as e:
            if e.response.status_code in [504]:
                cprint(f"HTTP error {e.response.status_code}, retrying...", 'red')
                time.sleep(requests_retry_interval)
            raise e

    return response


def requests_retriable_put(url: str, **kwargs) -> Response:
    while True:
        try:
            response = requests.put(url, **kwargs)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            cprint("Connection error, retrying...", 'red')
            time.sleep(requests_retry_interval)
        except requests.exceptions.RequestException as e:
            if e.response.status_code in [504]:
                cprint(f"HTTP error {e.response.status_code}, retrying...", 'red')
                time.sleep(requests_retry_interval)
            raise e

    return response


def requests_retriable_get(url: str, **kwargs) -> Response:
    new_kwargs = kwargs
    max_attempts = kwargs['max_attempts'] if 'max_attempts' in kwargs else 0
    new_kwargs.pop('max_attempts', None)
    attempts = 0

    while True:
        attempts += 1

        try:
            response = requests.get(url, **new_kwargs)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempts == max_attempts:
                raise PluginError('Max connection attempts exceeded')

            cprint("Connection error, retrying...", 'red')
            time.sleep(requests_retry_interval)
        except requests.exceptions.RequestException as e:
            if e.response.status_code in [504]:
                cprint(f"HTTP error {e.response.status_code}, retrying...", 'red')
                time.sleep(requests_retry_interval)
            raise e

    return response


def img_key_variance(item):
    return item[1]


def img_key_order(item):
    return item[0]


def list_files(parent_dir):
    file_list = []
    list_files_inner(parent_dir, None, file_list)

    file_list = [os.path.join(os.path.split(parent_dir)[-1], f) for f in file_list]

    return file_list


def list_files_inner(parent, path, file_list):
    joined_path = os.path.join(parent, path) if path else parent
    for curr in os.scandir(joined_path):
        if curr.is_file():
            file_list.append(os.path.relpath(curr.path, parent))
        elif curr.is_dir():
            list_files_inner(parent, curr.path, file_list)


def get_mime_type(path):
    try:
        with open(path, 'rb') as infile:
            return magic.from_buffer(infile.read(1048576), mime=True)
    except Exception as e:
        raise MagicError("Metadata error, check your 'magic' installation: {0}".format(str(e)))


def mp3_info(path):

    results = {}

    stream = bitstring.ConstBitStream(filename=path)

    # look for Xing
    xing_header = stream.find("0x58696E67", bytealigned=True)

    if xing_header:
        results['xing_header'] = "XING"
        results['method'] = "VBR"
        stream.bytepos += 4
        xing_flags = stream.read("uint:32")
        if xing_flags & 1:					# skip frames field
            stream.bytepos += 4
        if xing_flags & 2:					# skip bytes field
            stream.bytepos += 4
        if xing_flags & 4:					# skip TOC
            stream.bytepos += 100
        if xing_flags & 8:
            xing_vbr_quality = stream.read("uint:32")
            results['xing_vbr_v'] = 10 - math.ceil(xing_vbr_quality/10)
            results['xing_vbr_q'] = 10 - xing_vbr_quality % 10

        # LAME versions < 3.90 do not contain encoder info, and will not be picked up by this. Treat as VBR
        lame_version = stream.read("bytes:9")
        if lame_version[0:4] == b"LAME":
            results['xing_header'] = "LAME"

            # noinspection PyBroadException
            try:
                # allow for broken/hacked LAME versions, treat as regular VBR
                results['lame_version'] = lame_version[4:].decode().strip()
                results['lame_tag_revision'] = stream.read("uint:4")
                results['lame_vbr_method'] = stream.read("uint:4")
                stream.bytepos += 9
                results['lame_nspsytune'] = stream.read("bool")
                results['lame_nssafejoint'] = stream.read("bool")
                results['lame_nogap_next'] = stream.read("bool")
                results['lame_nogap_previous'] = stream.read("bool")

                if results['lame_version'][-1] == ".":
                    results['lame_version'] = results['lame_version'][:-1]
            except Exception:
                results['method'] = "VBR"

        return results

    info_header = stream.find("0x496E666F", bytealigned=True)
    if info_header:
        results['xing_header'] = "INFO"
        results['method'] = "CBR"
        return results

    vbri_header = stream.find("0x56425249", bytealigned=True)
    if vbri_header:
        results['xing_header'] = "VBRI"
        results['method'] = "VBR"
        return results

    # Assume CBR...
    results['method'] = "CBR"

    return results


def imdb_id_to_url(imdb_id: str) -> str:
    return "https://www.imdb.com/title/tt{0}/".format(imdb_id)


def imdb_url_to_id(imdb_url: str) -> str:
    imdb_id_match = re.findall(r"imdb\.com/title/tt(\d{7,8})", imdb_url)

    if imdb_url and not imdb_id_match:
        raise ValidationError(["Invalid IMDb URL"])

    if imdb_id_match:
        return imdb_id_match[0]


def verify_imdb(imdb_id: str) -> None:
    # imdb._logging.setLevel("error")
    logging.info('IMDb querying...'),
    imdb_site = imdb.Cinemagoer()

    try:
        imdb_movie = imdb_site.get_movie(imdb_id)
    except IMDbDataAccessError:
        logging.error("Invalid IMDb ID: {0}".format(imdb_id))
        raise ValidationError(["Invalid IMDb ID: {0}".format(imdb_id)])
    logging.info("IMDb verified: \"{0}\"".format(imdb_movie))


def extract_metadata(path: str) -> Tuple[int, int, Dict]:
    file_list = list_files(path)

    parent_dir = os.path.abspath(os.path.join(path, os.pardir)) + os.path.sep
    total_duration = 0
    smarthash_path_info = {}
    num_video_files = 0
    total_media_size = 0

    # extract metadata into a path -> json-metadata map
    for file in file_list:
        ext = os.path.splitext(file)[1].lower()
        # ignore extensions blacklist
        if ext in blacklist_media_extensions:
            continue

        file_path = os.path.join(parent_dir, file)
        mime_type = get_mime_type(file_path)
        mime_prefix = mime_type.split("/")[0]

        if mime_prefix in ["audio", "video"] or ext in whitelist_video_extensions \
                or ext in whitelist_audio_extensions:
            # TODO split calculation into audio and video
            total_media_size += os.path.getsize(file_path)
            smarthash_info = OrderedDict()
            smarthash_info['mediainfo'] = []
            if mime_type:
                smarthash_info['mime_type'] = mime_type

            media_info = MediaInfo.parse(file_path)
            for track in media_info.tracks:
                track_map = track.to_data()

                # remove the full path for privacy's sake
                if track_map['track_type'] == "General":
                    track_map['complete_name'] = track_map['complete_name'].replace(parent_dir, "")
                    track_map['folder_name'] = track_map['folder_name'].replace(parent_dir, "")
                    if 'duration' in track_map:
                        total_duration += track_map['duration']

                smarthash_info['mediainfo'].append(track_map)

            # extract audio tags
            if mime_prefix == "audio" or ext in whitelist_audio_extensions:
                smarthash_info['tags'] = OrderedDict()

                mutagen_file = mutagen.File(file_path)  # easy=True

                if not mutagen_file:
                    continue

                tags = {}
                for k in mutagen_file:
                    # filter out >1500 char (presumably binary) tags, except for comment/lyrics
                    if hasattr(mutagen_file[k], 'text') and len(mutagen_file[k].text) and \
                            (len(mutagen_file[k].text) < 1500 or k in ["USLT", "COMM"]):
                        tags[k] = [str(x) for x in mutagen_file[k].text]
                    elif isinstance(mutagen_file[k], list):
                        tags[k] = [str(x) for x in mutagen_file[k]]

                for tag in sorted(tags):
                    smarthash_info['tags'][tag] = tags[tag]

                if isinstance(mutagen_file.tags, VCFLACDict):
                    smarthash_info['tag_type'] = 'FLAC'
                elif isinstance(mutagen_file.tags, ID3):
                    smarthash_info['tag_type'] = 'ID3'
                smarthash_info['length'] = mutagen_file.info.length
                smarthash_info['bitrate'] = mutagen_file.info.bitrate

            # Xing frame info
            if mime_type == "audio/mpeg" or ext == ".mp3":
                smarthash_info['mp3_info'] = mp3_info(file_path)

            # count the number of video files
            if (mime_prefix == "video" or ext in whitelist_video_extensions) \
                    and ext not in blacklist_media_extensions:
                num_video_files += 1

            smarthash_path_info[file] = smarthash_info

    return total_media_size, total_duration, smarthash_path_info


def filter_screenshot_paths(paths_in: List[str], root: str) -> List[str]:
    """For large numbers of videos, group by subfolder (multilevel) and return one per subfolder"""
    if len(paths_in) <= 8:
        return paths_in

    # Calculate the max prefix length (the max depth in the structure)
    max_prefix_length = max([len(Path(x.replace(root, '')[1:]).parts[:-1]) for x in paths_in])
    curr_prefix_length = max_prefix_length
    last_set = paths_in

    # Start with the longest possible prefix. As the prefix shortens, there will be more matches per prefix
    while curr_prefix_length >= 0:
        curr_set = filter_screenshot_paths_inner(paths_in, root, curr_prefix_length)

        # set is too small, return first 8 from the last set
        if len(curr_set) <= 2 and curr_prefix_length <= max_prefix_length:
            return last_set[:8]

        if len(curr_set) <= 8:
            return curr_set

        # At the shortest possible prefix, return up to 8 matches
        if curr_prefix_length == 0:
            return curr_set[:8]

        curr_prefix_length -= 1
        last_set = curr_set


def filter_screenshot_paths_inner(paths_in: List[str], root: str, prefix_length: int) -> List[str]:
    """extract screenshots from one file per subfolder, for large numbers of files"""
    assert prefix_length >= 0

    screenshot_files = []
    screenshot_file_prefixes = []
    for screenshot_file in paths_in:
        parts = Path(screenshot_file.replace(root, '')[1:]).parts[:-1]  # only the folders, remove the filename
        prefix = Path(*parts[:min(len(parts), prefix_length)])

        if prefix not in screenshot_file_prefixes:
            screenshot_file_prefixes.append(prefix)
            screenshot_files.append(screenshot_file)
    return screenshot_files
