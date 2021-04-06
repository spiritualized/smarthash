import os, sys
from enum import Enum
from typing import List, Dict, Optional

from functions import PluginError, BulkMode
from pluginmixin import PluginMixin


class ParamType(Enum):
	PATH = 1
	SELECT = 2
	TEXT = 3


class Param:
	def __init__(self, name: str, param_type: ParamType, label: str = None, default_value = None,
				 required: bool = True, options: List[str] = None) -> None:
		self.name = name
		self.param_type = param_type
		self.label = label
		self.default_value = default_value
		self.required = required
		self.options = options


class BasePlugin(PluginMixin):

	plugin_version = None
	title = None
	description = ""

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
