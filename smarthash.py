import logging
import os, sys, importlib, inspect, json, math, re
import time
from collections import OrderedDict
from typing import List

from libprick import Pricker, PrickError
from mutagen.flac import VCFLACDict
from mutagen.id3 import ID3
from release_dir_scanner import get_release_dirs

from BitTornado.Application.makemetafile import make_meta_file
from pymediainfo import MediaInfo
from termcolor import colored, cprint

import argparse
import colorama
import imdb
import mutagen

import requests, configparser, baseplugin, bitstring

import MIFormat
from functions import *
from config import *
from plugin.baseplugin import BasePlugin

smarthash_version = "2.4.0"


class SmartHash:

    def __init__(self):
        self.early_return = False
        self.init()

    def init(self):
        self.load_config()
        colorama.init()

        plugin_filenames = SmartHash.plugin_find()

        # basic parameters
        argparser = argparse.ArgumentParser()
        argparser.add_argument("path")
        argparser.add_argument('--version', action='version', version="SmartHash {0}".format(smarthash_version))
        argparser.add_argument("--plugin", help="specify a manual output script: " + ", ".join(plugin_filenames),
                               default="default")
        argparser.add_argument("--destination", help="specify a file destination")
        argparser.add_argument("--nfo-path", help="specify a nfo file/folder path manually")

        bulk = argparser.add_mutually_exclusive_group()
        bulk.add_argument("--bulk", action='store_true', help="process every item in the path individually")

        self.plugins = {}
        unique_arguments = {}

        for x in plugin_filenames:
            self.plugins[x] = importlib.import_module("Plugins." + x).SmarthashPlugin()

            if not hasattr(self.plugins[x], 'handle'):
                self.init_error("Could not import \"{0}\" plugin".format(x))
                continue

            if self.plugins[x].title not in self.config:
                self.config[self.plugins[x].title] = {}

            # store unique argparse argument registrations
            for arg in self.plugins[x].arguments:
                if arg.argument not in unique_arguments:
                    unique_arguments[arg.argument] = arg.kwargs

                elif 'help' in unique_arguments[arg.argument] and 'help' in arg.kwargs \
                        and unique_arguments[arg.argument]['help'] != arg.kwargs['help']:
                    logging.warning("Ignoring argument from plugin '{plugin}': {arg}"
                                    .format(plugin=self.plugins[x].description, arg=arg.argument))

        # register arguments with argparse
        for arg in unique_arguments:
            argparser.add_argument(arg, **unique_arguments[arg])

        self.args = argparser.parse_args()

        if self.args.plugin not in self.plugins:
            logging.error("Invalid plugin: {0}".format(self.args.plugin))
            sys.exit(1)

        # update the selected plugin
        if self.args.plugin:
            self.plugin_update(self.plugins[self.args.plugin])

        self.plugins[self.args.plugin].validate_parameters(self.args)

    def load_config(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))

    def save_config(self) -> None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename), 'w') as configfile:
            self.config.write(configfile)

    @staticmethod
    def plugin_find() -> List[str]:
        plugin_path = SmartHash.get_plugin_path()
        plugin_filenames = [str(f) for f in os.listdir(plugin_path) if os.path.isfile(os.path.join(plugin_path, f))]
        plugin_filenames = [ f.split(".")[0] for f in plugin_filenames if f.endswith(".py") ]

        if os.path.exists(os.path.join(plugin_path, '__temp__.py')):
            os.remove(os.path.join(plugin_path, '__temp__.py'))

        return plugin_filenames

    def plugin_update(self, plugin: BasePlugin):
        plugin.validate_settings()

        new_plugin_src = None
        while True:
            try:
                new_plugin_src = plugin.get_update(smarthash_version)
                self.clear_error()
                break
            except (requests.exceptions.ConnectionError, ServerError):
                self.init_error("Connection error: plugin could not check for updates. retrying...")
                if self.early_return:
                    return

                time.sleep(1)

        if new_plugin_src != "":
            try:
                plugin_path = self.get_plugin_path()
                with open(os.path.join(plugin_path, '__temp__.py'), 'w+') as plugin_file:
                    plugin_file.write(new_plugin_src)
                new_plugin_module = importlib.import_module("Plugins.__temp__").SmarthashPlugin()

                os.remove(os.path.join(plugin_path, plugin.get_filename()))
                os.rename(os.path.join(plugin_path, new_plugin_module.get_filename()),
                          os.path.join(plugin_path, plugin.get_filename()))
                cprint("'{0}' plugin updated from {1} to {2}".format(new_plugin_module.description,
                                                                     plugin.plugin_version,
                                                                     new_plugin_module.plugin_version))
                self.plugins[plugin.get_filename()] = new_plugin_module
            except:
                cprint("Failed updating to new version of '{0}'".format(plugin.description))
                sys.exit(1)


    @staticmethod
    def get_plugin_path() -> str:
        # get the root directory
        root_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            root_dir = sys._MEIPASS

        # list the plugin directory for external imports
        return os.path.join(root_dir, "Plugins")


    def process(self):
        path = os.path.abspath(smarthash.args.path)

        # check absolute
        if not os.path.isdir(path):
            cprint("Path does not exist, or is not a directory", 'red')
            sys.exit(1)

        if self.args.bulk:
            bulk_mode = self.plugins[self.args.plugin].get_bulk_mode(self.args)
            if bulk_mode == BulkMode.STANDARD:
                for item in os.scandir(path):
                    curr = os.path.join(path, item)
                    if os.path.isdir(curr):
                        self.process_folder_wrapper(curr)

            elif bulk_mode == BulkMode.MUSIC:
                for release_dir in get_release_dirs(path):
                    self.process_folder_wrapper(release_dir)

            else:
                raise PluginError('Selected plugin does not handle bulk mode correctly')

        else:
            self.process_folder_wrapper(path)

    def process_folder_wrapper(self, path: str):
        try:
            self.process_folder(path, self.plugins[self.args.plugin], self.args.nfo_path)
            cprint("Done{0}\n".format(" " * 40), 'green', end='\r')

        except ValidationError as e:
            for error in e.errors:
                if len(error) > 400:
                    error = "<error message is too long to display>"
                cprint("Error: {0}".format(error), 'red')

        except (MagicError, PluginError) as e:
            cprint(e.error, 'red')

        except ServerError:
            cprint("Server error, retrying...", "red")
            time.sleep(1)
            self.process_folder_wrapper(path)

    def process_folder(self, path: str, plugin: BasePlugin, nfo_path: str=None):

        logging.info("----------------------------\n{0}".format(path))
        print("\n{0}".format(path))

        file_list = listFiles(path)

        parent_dir = os.path.abspath(os.path.join(path, os.pardir)) + os.path.sep
        total_duration = 0
        smarthash_path_info = {}
        num_video_files = 0
        self.total_media_size = 0

        # extract metadata into a path -> json-metadata map
        for file in file_list:
            ext = os.path.splitext(file)[1].lower()
            # ignore extensions blacklist
            if ext in blacklist_media_extensions:
                continue

            file_path = os.path.join(parent_dir, file)
            mime_type = get_mime_type(file_path)
            mime_prefix = mime_type.split("/")[0]

            if mime_prefix in ["audio", "video"] or ext in whitelist_video_extensions or ext in whitelist_audio_extensions:
                self.total_media_size += os.path.getsize(file_path)
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
                        if hasattr(mutagen_file[k], 'text') and \
                                (len(mutagen_file[k].text) < 1500 or k in ["USLT", "COMM"]) and len(mutagen_file[k].text):
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
                    smarthash_info['mp3_info'] = Mp3Info(file_path)

                # count the number of video files
                if (mime_prefix == "video" or ext in whitelist_video_extensions) and ext not in blacklist_media_extensions:
                    num_video_files += 1

                smarthash_path_info[file] = smarthash_info

        # read nfos from main path
        nfo_filenames = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        nfo_filenames = [f for f in nfo_filenames if f.lower().endswith(".nfo")]

        nfos = []
        for f in nfo_filenames:
            nfos.append(read_nfo(os.path.join(path, f)))

        # manual nfo path
        if nfo_path:
            if os.path.isfile(nfo_path) and nfo_path.lower().endswith(".nfo"):
                nfos.append(read_nfo(nfo_path))
            elif os.path.isdir(nfo_path):
                nfo_filenames = [f for f in os.listdir(nfo_path)
                                 if os.path.isfile(os.path.join(nfo_path, f))]

                nfo_filenames = [f for f in nfo_filenames if f.lower().endswith(".nfo")]
                for f in nfo_filenames:
                    nfos.append(read_nfo(os.path.join(nfo_path, f)))

        imdb_id = None
        genre = None
        nfo = ''

        for curr_nfo in nfos:
            imdb_id_match = re.findall(r"imdb\.com/title/tt(\d{7}\d?)", curr_nfo)
            if imdb_id_match:
                imdb_id = imdb_id_match[0]
                nfo = curr_nfo

        # default nfo
        if len(nfos) > 0 and not imdb_id:
            nfo = nfos[0]

        if 'imdb-id' in plugin.options and self.args.imdb_id:
            # manual imdb_id override
            imdb_id = self.args.imdb_id

        # make sure the IMDb ID exists
        if imdb_id:

            # imdb._logging.setLevel("error")
            cprint('IMDb querying...\r', end='\r'),
            imdb_site = imdb.IMDb()

            imdb_movie = imdb_site.get_movie(imdb_id)
            if not imdb_movie:
                cprint("Invalid IMDb ID: {0}".format(imdb_id), "red")
                sys.exit(1)
            logging.info("IMDb verified: \"{0}\"".format(imdb_movie))

            genre = choose_genre(imdb_movie['genres'])

        params = {
            'blacklist_file_extensions': [x.lower() for x in blacklist_file_extensions],
            'blacklist_path_matches': [x.lower() for x in blacklist_path_matches],
            'comment': "Generated with SmartHash {0}".format(smarthash_version),
            'smarthash_version': smarthash_version,
        }

        plugin.early_validation(path, {
            'args': self.args,
            'smarthash_info': smarthash_path_info,
            'title': os.path.basename(path),
            'imdb_id': imdb_id,
            'genre': genre,
            'params': params
        })

        # hash the folder
        metainfo = make_meta_file(path, None, params=params, progress=self.hash_progress_callback)
        #print()

        pricker = Pricker(self.pricker_progress_callback)

        # lookup gathered metadata and insert into the torrent file metainfo
        for file in metainfo['info']['files']:
            file_path = os.path.join(os.path.basename(path), *file['path'])

            if file_path in smarthash_path_info:
                file['smarthash_info'] = json.dumps(smarthash_path_info[file_path])

                # calculate a pricker hash for audio files
                ext = os.path.splitext(file_path)[1].lower()
                if smarthash_path_info[file_path]['mime_type'].split('/')[0] in ['audio', 'video'] or \
                    ext in whitelist_video_extensions or ext in whitelist_audio_extensions:
                    try:
                        pricker.open(os.path.join(path, *file['path']))
                        file['pricker'] = pricker.hexdigest()
                        metainfo['pricker_version'] = pricker.version()
                    except PrickError:
                        pass

        formatted_mediainfo = ""
        extracted_images = []

        screenshot_files = []

        # extract MediaInfo
        for file in metainfo['info']['files']:
            file_path = os.path.join(path, *file['path'])
            ext = os.path.splitext(file_path)[1].lower()
            path_key = os.path.join(metainfo['info']['name'], *file['path'])
            mime_type = smarthash_path_info[path_key]['mime_type'] \
                if path_key in smarthash_path_info else get_mime_type(file_path)
            mime_prefix = mime_type.split("/")[0]

            # for video files, compose a standard(ish) MediaInfo text output
            if (mime_prefix == "video" or ext in whitelist_video_extensions) and ext not in blacklist_media_extensions:
                if formatted_mediainfo != "":
                    formatted_mediainfo += "\n{0}\n".format("-" * 70)
                formatted_mediainfo += MIFormat.MItostring(
                    smarthash_path_info[os.path.join(os.path.basename(path), *file['path'])]['mediainfo'])

                screenshot_files.append(file_path)

        if "video-screenshots" in plugin.options:
            extracted_images = self.extractImages(screenshot_files)

        # collect the dataset for the plugin
        data = {'smarthash_version': smarthash_version,
                'args': self.args,
                'path': path,
                'title': os.path.split(path)[-1],
                'total_duration': total_duration,
                'mediainfo': formatted_mediainfo,
                'extracted_images': extracted_images,
                'torrent_file': metainfo.gettorrent(),
                'nfo': nfo,
                }

        if imdb_id:
            data['imdb_id'] = imdb_id
        if genre:
            data['genre'] = genre

        plugin.handle(data)

        # if an operation succeeded, write out the config
        self.save_config()

    def extractImages(self, image_paths: List[str]) -> List:
        count = 0

        images_per_video_file = 4
        if len(image_paths) in [2, 3]:
            images_per_video_file = 2
        elif len(image_paths) > 3:
            images_per_video_file = 1

        n2 = images_per_video_file * 2 + 10
        if n2 < 10:
            n2 = 10

        images = []

        for path in image_paths:
            vidcap = cv2.VideoCapture(path)

            # take frames at regular intervals from a range excluding the first and last 10% of the file
            frame_count = vidcap.get(cv2.CAP_PROP_FRAME_COUNT)
            frame_count_10 = math.floor(frame_count / 10)
            interval = math.floor((frame_count - frame_count_10 * 2) / (n2 + 1))

            tmp_images = []
            tmp_variances = []

            for i in range(0, n2):
                vidcap.set(cv2.CAP_PROP_POS_FRAMES, (frame_count_10 + i * interval))  # added this line
                success, image = vidcap.read()
                success, buf = cv2.imencode(".jpeg", image)

                variance = cv2.Laplacian(image, cv2.CV_64F).var()
                tmp_images.append(buf.tobytes())
                tmp_variances.append([i, variance])


                count += 1
                self.image_extaction_progress_callback(count, images_per_video_file*len(image_paths))

            # select the N candidates with the highest variance, preserving order
            tmp_variances = sorted(tmp_variances, key=imgKeyVariance, reverse=True)[0:images_per_video_file]
            tmp_variances = sorted(tmp_variances, key=imgKeyOrder)

            images.append([tmp_images[x[0]] for x in tmp_variances])

        return images

    def hash_progress_callback(self, amount) -> None:
        print('Hashing: %.1f%% complete\r' % (amount * 100), end='\r')


    def pricker_progress_callback(self, bytes) -> None:
        print('Hashing again: %.1f%% complete\r' % (bytes / self.total_media_size * 100), end='\r')

    def image_extaction_progress_callback(self, x: int, total_images: int) -> None:
        print('Extracting images: %.1f%% complete\r' % (x / total_images * 100), end='\r')


    def fatal_error(self, msg: str) -> None:
        logging.error(msg)
        sys.exit(1)

    def init_error(self, msg: str) -> None:
        cprint(msg, 'red')

    def clear_error(self) -> None:
        pass

    def terminate(self) -> None:
        self.early_return = True


if __name__ == "__main__":

    smarthash = SmartHash()

    smarthash.process()
