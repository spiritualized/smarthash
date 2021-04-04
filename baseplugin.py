import os, sys

from functions import PluginError, BulkMode
from pluginmixin import PluginMixin


class BasePlugin(PluginMixin):

	plugin_version = "2.0.0"
	title = None
	description = ""
	options = []

	def get_title(self):
		if not self.title:
			raise PluginError('Plugin does not have a title')
		return "{title} v{version}".format(title=self.title, version=self.plugin_version)

	def get_filename(self):
		return os.path.basename(sys.modules[self.__module__].__file__)

	def get_bulk_mode(self, args) -> BulkMode:
		return BulkMode.STANDARD

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
