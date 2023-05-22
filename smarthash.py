import importlib

# noinspection PyPackageRequirements
import cv2
import requests.utils

from OutputPlugins.base_output import OutputPlugin
from OutputPlugins.deluge import Deluge
from OutputPlugins.qbittorrent import QBittorrent
from OutputPlugins.transmission import Transmission
from libprick import Pricker, PrickError
from release_dir_scanner import get_release_dirs

from BitTornado.Application.makemetafile import make_meta_file

import argparse
import colorama

import configparser

import MIFormat
from functions import *
from config import *
from baseplugin import BasePlugin, PluginOutput
from pluginmixin import UIMode, ParamType
from tools.process_lock import ProcessLock
from tools.skip_cache import SkipCache

smarthash_version = "3.0.0"
requests.utils.default_user_agent = lambda: f"SmartHash/{smarthash_version}"


class PluginUIInterface:
    """Interface allowing plugins to communicate with the UI"""
    def __init__(self, smarthash_obj: "SmartHash", plugin: "BasePlugin"):
        self.smarthash_obj = smarthash_obj
        self.plugin = plugin

    def progress_callback(self, message: str, incremental: bool = True) -> None:
        self.smarthash_obj.plugin_progress_callback(f"[{self.plugin.get_title()}] {message}", incremental)


class SmartHash:

    def __init__(self):
        self.early_return = False
        self.total_media_size = None
        self.config = None
        self.args = None
        self.plugins = {}
        self.output_plugin = None
        self.skip_cache = SkipCache()
        self.lock = ProcessLock()
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
        argparser.add_argument("--skip-video-rehash", action="store_true")
        argparser.add_argument("--disable-blacklist", action="store_true", help="Include unwanted files in torrent")
        argparser.add_argument("--disable-skip-cache", action="store_true",
                               help="Disables caching of content rejected by a plugin")
        argparser.add_argument("--bulk", action='store_true', help="process every item in the path individually")

        argparser.add_argument("--bulk-sleep-interval", type=int, choices=range(1, 60), default=0,
                               help="Sleep interval (in minutes) between successful bulk mode items")

        unique_params = {}

        for x in plugin_filenames:
            try:
                self.plugins[x] = importlib.import_module("Plugins." + x).SmarthashPlugin()

                if self.plugins[x].title in self.config:
                    self.plugins[x].set_config(self.config[self.plugins[x].title])
            except PluginError as e:
                logging.error(f"Could not import '{x}' plugin: {e.error}")
                del self.plugins[x]
                continue

            if self.plugins[x].title not in self.config:
                self.config[self.plugins[x].title] = {}

            # store unique plugin parameters
            for param in self.plugins[x].parameters:
                if param.name not in unique_params:
                    unique_params[param.name] = param
                elif unique_params[param.name].help != param.help and x not in ['default', 'save']:
                    logging.warning("Ignoring argument from plugin '{plugin}': {param}"
                                    .format(plugin=self.plugins[x].title, param=param.name))

        # register parameters with argparse
        for param in unique_params.values():
            if param.ui_mode not in [UIMode.CLI, UIMode.BOTH] or param.display_only:
                continue

            arg_name = '--' + param.name.replace(' ', '-').replace('_', '-')
            kwargs = {}
            if param.help:
                kwargs['help'] = param.help
            if param.default_value:
                kwargs['default'] = param.default_value
            if param.param_type in [ParamType.SELECT, ParamType.RADIO]:
                kwargs['choices'] = [x.lower() for x in param.options]

            if param.param_type == ParamType.CHECKBOX:
                kwargs['action'] = 'store_true'
            elif param.force_lowercase:
                kwargs['type'] = str.lower

            argparser.add_argument(arg_name, **kwargs)

        self.args = argparser.parse_args()

        if self.args.plugin not in self.plugins:
            logging.error("Invalid plugin: {0}".format(self.args.plugin))
            sys.exit(1)

        if self.args.disable_skip_cache:
            self.skip_cache.disable()

        # update the selected plugin
        if self.args.plugin:
            self.plugin_update(self.plugins[self.args.plugin])

        self.plugins[self.args.plugin].validate_parameters(self.args)

        # set up output plugin
        output_plugin = self.get_config_value('SmartHash', 'output to').lower()
        try:
            if output_plugin in ['', 'none']:
                self.output_plugin = OutputPlugin()
            elif output_plugin == 'deluge':
                self.output_plugin = Deluge(self.config['deluge'])
            elif output_plugin == 'qbittorrent':
                self.output_plugin = QBittorrent(self.config['qBittorrent'])
            elif output_plugin == 'transmission':
                self.output_plugin = Transmission(self.config['Transmission'])
            else:
                raise PluginError(f"invalid option '{output_plugin}'")
        except PluginError as e:
            cprint(f"Output plugin '{output_plugin}' failed: {e.error}", 'red')
            sys.exit(1)

    def load_config(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))

    def save_config(self) -> None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename), 'w') as configfile:
            self.config.write(configfile)

    def get_config_value(self, section, attribute: str = None) -> str:
        if section not in self.config:
            return ''
        if attribute not in self.config[section]:
            return ''
        return self.config[section][attribute]


    @staticmethod
    def plugin_find() -> List[str]:
        plugin_path = SmartHash.get_plugin_path()
        plugin_filenames = [str(f) for f in os.listdir(plugin_path) if os.path.isfile(os.path.join(plugin_path, f))]
        plugin_filenames = [f.split(".")[0] for f in plugin_filenames if f.endswith(".py")]

        if os.path.exists(os.path.join(plugin_path, '__temp__.py')):
            os.remove(os.path.join(plugin_path, '__temp__.py'))

        return plugin_filenames

    def plugin_update(self, plugin: BasePlugin):
        plugin.validate_settings()

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

            except UpdateError as e:
                cprint(e.error, 'red')
                return

        if new_plugin_src != "":
            # noinspection PyBroadException
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
            except Exception:
                cprint("Failed updating to new version of '{0}'".format(plugin.description))
                sys.exit(1)

    @staticmethod
    def get_plugin_path() -> str:
        # get the root directory
        root_dir = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            # noinspection PyUnresolvedReferences,PyProtectedMember
            root_dir = sys._MEIPASS

        # list the plugin directory for external imports
        return os.path.join(root_dir, "Plugins")

    def process(self):
        path = os.path.abspath(self.args.path)

        # check absolute
        if not os.path.isdir(path):
            cprint("Path does not exist, or is not a directory", 'red')
            sys.exit(1)

        if self.args.bulk:
            bulk_mode = self.plugins[self.args.plugin].get_bulk_mode(self.args)
            if bulk_mode == BulkMode.STANDARD:
                for item in sorted(os.listdir(path)):
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

        self.skip_cache.save()

    def process_folder_wrapper(self, path: str):
        if self.skip_cache.in_cache(self.args.plugin, path):
            cprint(f"Skipped [cache]: {path}", 'yellow')
            return

        try:
            self.process_folder(path, self.plugins[self.args.plugin])
            cprint("Done{0}".format(" " * 40), 'green')

            if self.args.bulk and self.args.bulk_sleep_interval:
                print(f"Sleeping for {self.args.bulk_sleep_interval} minutes...")
                time.sleep(self.args.bulk_sleep_interval * 60)

        except ConflictError as e:
            self.skip_cache.add(self.args.plugin, path)
            cprint(f"Skipped: {e.message}", 'yellow')
            self.lock.release()
        except ValidationError as e:
            for err in e.errors:
                if len(err) > 400:
                    err = "<error message is too long to display>"
                cprint("Error: {0}".format(err), 'red')
            self.lock.release()

        except (MagicError, PluginError) as e:
            cprint(e.error, 'red')
            self.lock.release()

        except ServerError as e:
            cprint(f"Server error [{e.error}], retrying in {requests_retry_interval} seconds...", "red")
            time.sleep(requests_retry_interval)
            self.process_folder_wrapper(path)

    def process_folder(self, path: str, plugin: BasePlugin):

        logging.info("----------------------------\n{0}".format(path))
        print("\n{0}".format(path))

        self.lock.acquire()

        self.total_media_size, total_duration, smarthash_path_info = extract_metadata(path)

        blacklist_path_matches_enabled = [] if self.args.disable_blacklist else blacklist_path_matches

        blacklist_file_extensions_enabled = blacklist_file_extensions + plugin.get_blacklist_file_extensions(self.args)

        params = {
            'blacklist_file_extensions': [x.lower() for x in blacklist_file_extensions_enabled],
            'blacklist_path_matches': [x.lower() for x in blacklist_path_matches_enabled],
            'comment': "Generated with SmartHash {0}".format(smarthash_version),
            'smarthash_version': smarthash_version,
        }

        plugin.early_validation(path, {
            'args': self.args,
            'smarthash_info': smarthash_path_info,
            'title': os.path.basename(path),
            'params': params
        })

        # hash the folder
        metainfo = make_meta_file(path, None, params=params, progress=self.hash_progress_callback)

        pricker = Pricker(self.pricker_progress_callback)

        # lookup gathered metadata and insert into the torrent file metainfo
        for file in metainfo['info']['files']:
            file_path = os.path.join(os.path.basename(path), *file['path'])

            if file_path in smarthash_path_info:
                file['smarthash_info'] = json.dumps(smarthash_path_info[file_path])

                # calculate a pricker hash for audio files
                ext = os.path.splitext(file_path)[1].lower()
                mime_prefix = smarthash_path_info[file_path]['mime_type'].split('/')[0]

                if mime_prefix == 'audio' or ext in whitelist_audio_extensions or \
                        (not self.args.skip_video_rehash and
                         (mime_prefix == 'video' or ext in whitelist_audio_extensions)):

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
                formatted_mediainfo += MIFormat.mediainfo_to_string(
                    smarthash_path_info[os.path.join(os.path.basename(path), *file['path'])]['mediainfo'])

                screenshot_files.append(file_path)

        if "video-screenshots" in plugin.options:
            extracted_images = self.extract_images(screenshot_files)

        # collect the dataset for the plugin
        data = {
            'smarthash_version': smarthash_version,
            'ui_interface': PluginUIInterface(self, plugin),
            'args': self.args,
            'path': path,
            'title': os.path.split(path)[-1],
            'smarthash_info': smarthash_path_info,
            'total_duration': total_duration,
            'mediainfo': formatted_mediainfo,
            'extracted_images': extracted_images,
            'torrent_file': metainfo.gettorrent(),
        }

        print("\rCalling plugin '{0}'...".format(plugin.get_title()))

        plugin_output = plugin.handle(data)
        assert isinstance(plugin_output, PluginOutput)

        if not isinstance(self.output_plugin, OutputPlugin):
            print(f"Calling {self.output_plugin.title}...")
        try:
            self.output_plugin.handle(plugin_output, os.path.dirname(path))
        except PluginError as e:
            cprint(f"Output plugin '{self.output_plugin.title}' failed: {e.error}", 'red')

        # if an operation succeeded, write out the config
        self.save_config()

        self.lock.release()

    def extract_images(self, screenshot_files: List[str]) -> List:
        count = 0

        images_per_video_file = 4
        if len(screenshot_files) in [2, 3]:
            images_per_video_file = 2
        elif len(screenshot_files) > 3:
            images_per_video_file = 1

        screenshot_files = filter_screenshot_paths(screenshot_files, self.args.path)

        n2 = images_per_video_file * 2 + 10
        if n2 < 10:
            n2 = 10

        images = []

        for path in screenshot_files:
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

                if success:
                    success, buf = cv2.imencode(".jpeg", image)

                    variance = cv2.Laplacian(image, cv2.CV_64F).var()
                    tmp_images.append(buf.tobytes())
                    tmp_variances.append([i, variance])
                else:
                    logging.error(f"Screenshot extraction failed ({i+1} of {n2})")

                count += 1
                self.image_extaction_progress_callback(count, n2*len(screenshot_files))

            # select the N candidates with the highest variance, preserving order
            num_images = min(images_per_video_file, len(tmp_images))
            tmp_variances = sorted(tmp_variances, key=img_key_variance, reverse=True)[0:num_images]
            tmp_variances = sorted(tmp_variances, key=img_key_order)

            images.append([tmp_images[x[0]] for x in tmp_variances])

        return images

    def hash_progress_callback(self, amount) -> None:
        print('\rHashing: %.1f%% complete' % (amount * 100), end='')

    def pricker_progress_callback(self, num_bytes) -> None:
        print('\rHashing again: %.1f%% complete' % (num_bytes / self.total_media_size * 100), end='')

    def image_extaction_progress_callback(self, x: int, total_images: int) -> None:
        print('\rExtracting images: %.1f%% complete' % (x / total_images * 100), end='')

    def plugin_progress_callback(self, message: str, incremental: bool) -> None:
        """Callback for slow plugin progress updates. Pass incremental=True to overwrite the previous line."""
        start = "\r" if incremental else ''
        print(f"{start}{message}", end='')

    def init_error(self, msg: str) -> None:
        cprint(msg, 'red')

    def clear_error(self) -> None:
        pass

    def terminate(self) -> None:
        self.early_return = True


if __name__ == "__main__":

    smarthash = SmartHash()

    smarthash.process()
