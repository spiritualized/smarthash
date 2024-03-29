from baseplugin import BasePlugin, PluginOutput
import os

from pluginmixin import Param, ParamType


class SmarthashPlugin(BasePlugin):

	plugin_version = "2.0.0"
	title = "Save torrent and metadata"
	description = "Writes extracted data out to a folder"
	options = ['video-screenshots']
	parameters = [
		Param('destination', ParamType.PATH, 'Save to: ', 'Select a destination folder',
			  help='Save torrent and metadata to a folder')
	]

	def handle(self, data) -> PluginOutput:

		meta_folder = data['path']+"_smarthash"

		# manual destination
		if data['args'].destination != self.parameters[0].default_value:
			meta_folder = self.manual_destination(data['args'].destination, data['title'])

		if os.path.isfile(meta_folder):
			raise ValueError("Output folder path is a file")

		if not os.path.isdir(meta_folder):
			os.makedirs(meta_folder)
		torrent_file_path = os.path.join(meta_folder, data['title'])+".torrent"

		if 'nfo' in data:
			with open(os.path.join(meta_folder, "nfo.nfo"), "w") as file:
				file.write(data['nfo'])
		if 'mediainfo' in data:
			with open(os.path.join(meta_folder, "mediainfo.txt"), "w") as file:
				file.write(data['mediainfo'])

		if 'extracted_images' in data:
			for file_images in data['extracted_images']:
				i = 0
				for image in file_images:
					with open(os.path.join(meta_folder, "screenshot_{0}.jpeg".format(i)), "wb") as file:
						file.write(image)
					i += 1

		with open(torrent_file_path, 'wb') as handle:
			handle.write(data['torrent_file'])

		return PluginOutput(data['torrent_file'])

	@staticmethod
	def manual_destination(destination: str, title: str) -> str:
		save_path = destination

		# if the output path ends with a path separator
		if save_path.endswith(os.sep) or save_path.endswith('/'):
			save_path += title

		save_path += "_smarthash"
		save_path = os.path.abspath(save_path)

		return save_path
