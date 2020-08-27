import os, sys

from pluginmixin import PluginMixin


class BasePlugin(PluginMixin):

	plugin_version = "1.0.0"
	description = ""
	options = []

	def get_filename(self):
		return os.path.basename(sys.modules[self.__module__].__file__)

	def validate_settings(self):
		pass

	def get_update(self, smarthash_version):
		return ""

	def validate_parameters(self, args):
		pass

	def early_validation(self, path, data):
		pass

	def handle(self, data):
		pass
