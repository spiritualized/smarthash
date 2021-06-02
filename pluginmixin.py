import os
import sys


class PluginArgument:

    def __init__(self, argument: str, **kwargs):
        self.argument = argument
        self.kwargs = kwargs


class PluginMixin:
    parameters = {}

    def __init__(self):
        self.hooks = []
        self.config = None

    def set_config(self, config) -> None:
        self.config = config

    def get_filename(self):
        return os.path.basename(sys.modules[self.__module__].__file__)

    def get_config_value(self, name: str):
        if name in self.config:
            return self.config[name]

        for param in self.parameters:
            if param.name == name:
                return param.default_value

    def create_valid(self) -> bool:
        return True