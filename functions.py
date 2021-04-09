import logging
import math, os, sys
import re
import time
from enum import Enum
from typing import List, Tuple

import cv2
import imdb
import requests
from imdb import IMDbDataAccessError
from requests import Response
from termcolor import colored, cprint
import magic
import bitstring
import json

from config import blacklist_file_extensions, blacklist_path_matches


class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors

class PluginError(Exception):
    def __init__(self, error: str):
        self.error = error

class ServerError(Exception):
    def __init__(self, error: str):
        self.error = error

class MagicError(Exception):
    def __init__(self, error: str):
        self.error = error

class BulkMode(Enum):
    STANDARD = 1
    MUSIC = 2

def error(msg):
    try:
        decoded = json.loads(msg)
        if 'errors' in decoded:
            if len(decoded['errors']) > 1:
                cprint("Error:", 'red')
                for error in decoded['errors']:
                    cprint(error, 'red')
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
        except requests.exceptions.ConnectionError:
            cprint("Connection error, retrying...", 'red')
            time.sleep(1)

    return response

def requests_retriable_put(url: str, **kwargs) -> Response:
    while True:
        try:
            response = requests.put(url, **kwargs)
            break
        except requests.exceptions.ConnectionError:
            cprint("Connection error, retrying...", 'red')
            time.sleep(1)

    return response

def requests_retriable_get(url: str, **kwargs) -> Response:
    while True:
        try:
            response = requests.get(url, **kwargs)
            break
        except requests.exceptions.ConnectionError:
            cprint("Connection error, retrying...", 'red')
            time.sleep(1)

    return response

def imgKeyVariance(item):
    return item[1]
def imgKeyOrder(item):
    return item[0]

def listFiles(parent_dir):
    file_list = []
    listFilesInner(parent_dir, None, file_list)

    for x in blacklist_path_matches:
        for file in file_list:
            if x.lower() in file.lower():
                file_list.remove(file)
                continue

    for x in blacklist_file_extensions:
        for file in file_list:
            if file.lower().endswith(x.lower()):
                file_list.remove(file)
                continue

    file_list = [os.path.join(os.path.split(parent_dir)[-1], f) for f in file_list]

    return file_list

def listFilesInner(parent, path, file_list):
    joined_path = os.path.join(parent, path) if path else parent
    for curr in os.scandir(joined_path):
        if curr.is_file():
            file_list.append(os.path.relpath(curr.path, parent))
        elif curr.is_dir():
            listFilesInner(parent, curr.path, file_list)

def get_mime_type(path):
    mime_type = ''
    try:
        with open(path, 'rb') as infile:
            return magic.from_buffer(infile.read(1048576), mime=True)
    except Exception as e:
        raise MagicError("Metadata error, check your 'magic' installation: {0}".format(str(e)))
    return mime_type

def Mp3Info(path):

    results = {}

    stream = bitstring.ConstBitStream(filename=path)

    # look for Xing
    Xing = stream.find("0x58696E67", bytealigned=True)

    if Xing:
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

            # allow for broken/hacked LAME versions, treat as regular VBR
            try:
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
            except:
                results['method'] = "VBR"

        return results

    Info = stream.find("0x496E666F", bytealigned=True)
    if Info:
        results['xing_header'] = "INFO"
        results['method'] = "CBR"
        return results

    VBRI = stream.find("0x56425249", bytealigned=True)
    if VBRI:
        results['xing_header'] = "VBRI"
        results['method'] = "VBR"
        return results

    # Assume CBR...
    results['method'] = "CBR"

    return results

def imdb_id_to_url(imdb_id: str) -> str:
    return "https://www.imdb.com/title/tt{0}/".format(imdb_id)

def imdb_url_to_id(imdb_url: str) -> str:
    imdb_id_match = re.findall(r"imdb\.com/title/tt(\d{7}\d?)", imdb_url)

    if imdb_url and not imdb_id_match:
        raise ValidationError(["Invalid IMDb URL"])

    if imdb_id_match:
        return imdb_id_match[0]

def verify_imdb(imdb_id: str) -> None:
    # imdb._logging.setLevel("error")
    logging.info('IMDb querying...'),
    imdb_site = imdb.IMDb()

    imdb_movie = imdb_site.get_movie(imdb_id)
    if not imdb_movie:
        logging.error("Invalid IMDb ID: {0}".format(imdb_id))
        raise ValidationError(["Invalid IMDb ID: {0}".format(imdb_id)])
    logging.info("IMDb verified: \"{0}\"".format(imdb_movie))