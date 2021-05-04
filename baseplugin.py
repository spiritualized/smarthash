import os, sys
from enum import Enum
from typing import List, Dict, Optional

from functions import PluginError, BulkMode
from pluginmixin import PluginMixin


class ParamType(Enum):
    PATH = 1
    SELECT = 2
    TEXT = 3
    CHECKBOX = 4
    RADIO = 5


class HookCommandType(Enum):
    UPDATE = 1
    VISIBLE = 2
    OPTIONS = 3
    RESET_DEFAULT = 4


class Param:
    def __init__(self, name: str, param_type: ParamType, label: str = None, default_value=None, required: bool = False,
                 options: List[str] = None, visible: bool = True, disabled: bool = False,
                 load_last_value: bool = True) -> None:
        self.name = name
        self.param_type = param_type
        self.label = label
        self.default_value = default_value
        self.required = required
        self.options = options
        self.visible = visible
        self.disabled = disabled
        self.load_last_value = load_last_value


class Hook:
    def __init__(self, element_name: str, function, exec_on_init=False):
        self.element_name = element_name
        self.function = function
        self.exec_on_init = exec_on_init


class HookCommand:
    def __init__(self, command_type: HookCommandType, element_name: str, value = None):
        self.command_type = command_type
        self.element_name = element_name
        self.value = value


class BasePlugin(PluginMixin):
    plugin_version = None
    title = None
    description = ""
    options = []

    def get_title(self) -> str:
        if not self.title:
            raise PluginError('Plugin does not have a title')
        version = " v{0}".format(self.plugin_version) if self.plugin_version else " [unversioned]"
        return "{title}{version}".format(title=self.title, version=version)

    def get_param(self, name: str) -> Optional[Param]:
        for param in self.parameters:
            if param.name == name:
                return param

    def get_bulk_mode(self, args) -> BulkMode:
        return BulkMode.STANDARD

    def validate_settings(self) -> None:
        pass

    def get_update(self, smarthash_version) -> str:
        return ""

    def validate_parameters(self, args) -> None:
        pass

    def early_validation(self, path, data) -> None:
        pass

    def handle(self, data) -> None:
        pass
