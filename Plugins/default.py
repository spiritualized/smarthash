import os

from baseplugin import BasePlugin, Param, ParamType

from functions import PluginError


class SmarthashPlugin(BasePlugin):

	plugin_version = "2.0.0"
	title = "Save to file"
	description = "Save a torrent file only"
	parameters = [
		Param('destination', ParamType.PATH, 'Save to: ', 'Select a destination folder',
			  help='Save torrent file to a folder')
	]

	def early_validation(self, path, data) -> None:
		if data['args'].destination:
			self.manual_destination(data['args'].destination, data['title'])

	def handle(self, data) -> None:

		save_path = data['path'] + ".torrent"

		# manual destination
		if data['args'].destination:
			save_path = self.manual_destination(data['args'].destination, data['title'])
		with open(save_path, 'wb') as handle:
			handle.write(data['torrent_file'])

	@staticmethod
	def manual_destination(destination: str, title: str) -> str:
		save_path = destination

		# if the output path ends with a path separator
		if save_path.endswith(os.sep) or save_path.endswith('/'):
			save_path += title

		# add a .torrent extension if it's missing
		if not save_path.lower().endswith(".torrent"):
			save_path += ".torrent"

		save_path = os.path.abspath(save_path)

		# check if the output path exists
		if not os.path.isdir(os.path.dirname(save_path)):
			raise PluginError("Output path {0} does not exist".format(os.path.dirname(save_path)))

		return save_path
