import hashlib
import os
import sys
from enum import Enum
from typing import Optional, List

from BitTornado.Meta.bencode import bdecode, bencode
from functions import PluginError


class ParamType(Enum):
    PATH = 1
    SELECT = 2
    TEXT = 3
    CHECKBOX = 4
    RADIO = 5


class UIMode(Enum):
    CLI = 1
    GUI = 2
    BOTH = 3


class HookCommandType(Enum):
    UPDATE = 1
    VISIBLE = 2
    OPTIONS = 3
    RESET_DEFAULT = 4


class PluginOutput:
    def __init__(self, torrent_data):
        self.torrent_data = torrent_data

    def get_hex_hash(self) -> str:
        return hashlib.sha1(bencode(bdecode(self.torrent_data)['info'])).hexdigest()


class Param:
    def __init__(self, name: str, param_type: ParamType, label: str = None, default_value=None, help: str = None,
                 type: type = None, force_lowercase: bool = False, required: bool = False, options: List[str] = None,
                 visible: bool = True, disabled: bool = False, display_only: bool = False,
                 ui_mode: UIMode = UIMode.BOTH, load_last_value: bool = True) -> None:
        self.name = name
        self.param_type = param_type
        self.label = label
        self.default_value = default_value
        self.help = help
        self.type = type
        self.force_lowercase = force_lowercase
        self.required = required
        self.options = options
        self.visible = visible
        self.disabled = disabled
        self.display_only = display_only
        self.ui_mode = ui_mode
        self.load_last_value = load_last_value


class Hook:
    def __init__(self, element_name: str, function, exec_on_init: bool = False, exec_on_default: bool = False):
        self.element_name = element_name
        self.function = function
        self.exec_on_init = exec_on_init
        self.exec_on_default = exec_on_default


class HookCommand:
    def __init__(self, command_type: HookCommandType, element_name: str, value=None):
        self.command_type = command_type
        self.element_name = element_name
        self.value = value


class PluginArgument:

    def __init__(self, argument: str, **kwargs):
        self.argument = argument
        self.kwargs = kwargs


class PluginMixin:
    plugin_version = None
    title = None
    description = ""
    options = []
    parameters = {}

    def __init__(self):
        self.hooks = []
        self.config = {}

    def set_config(self, config) -> None:
        self.config = config

    def get_title(self) -> str:
        """Return a string containing the title of the plugin"""
        if not self.title:
            raise PluginError('Plugin does not have a title')
        version = " v{0}".format(self.plugin_version) if self.plugin_version else " [unversioned]"
        return "{title}{version}".format(title=self.title, version=version)

    def get_filename(self):
        return os.path.basename(sys.modules[self.__module__].__file__)

    def get_config_value(self, name: str):
        if name in self.config:
            return self.config[name]

        for param in self.parameters:
            if param.name == name:
                return param.default_value

    def get_param(self, name: str) -> Optional[Param]:
        """
        Retreive a Plugin Parameter by name
        :param name: string identifying the requested parameter
        :return: the requested parameter
        """
        for param in self.parameters:
            if param.name == name:
                return param

    def create_valid(self) -> bool:
        return True
