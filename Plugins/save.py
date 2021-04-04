from baseplugin import BasePlugin, Param, ParamType
import os


class SmarthashPlugin(BasePlugin):

	plugin_version = "2.0.0"
	title = "Save torrent and metadata"
	description = "Writes extracted data out to a folder"
	options = ['video-screenshots']
	parameters = [
		Param('destination', ParamType.PATH, 'Select a destination folder')
	]

	def handle(self, data) -> None:

		meta_folder = data['path']+"_smarthash"
		if os.path.isfile(meta_folder):
			raise ValueError("Invalid filename")
		if not os.path.isdir(meta_folder):
			os.makedirs(meta_folder)
		torrent_file_path = os.path.join(data['path']+"_smarthash", data['title'])+".torrent"

		if 'nfo' in data:
			with open(os.path.join(data['path']+"_smarthash", "nfo.nfo"), "w") as file:
				file.write(data['nfo'])
		if 'mediainfo' in data:
			with open(os.path.join(data['path']+"_smarthash", "mediainfo.txt"), "w") as file:
				file.write(data['mediainfo'])

		if 'extracted_images' in data:
			for file_images in data['extracted_images']:
				i = 0
				for image in file_images:
					with open(os.path.join(data['path']+"_smarthash", "screenshot_{0}.jpeg".format(i)), "wb") as file:
						file.write(image)
					i += 1

		with open(torrent_file_path, 'wb') as handle:
			handle.write(data['torrent_file'])
