import os


class TorrentHandler:

	description = "Writes extracted data out to a folder"
	options = ['video-screenshots']

	def attach_arguments(self, argparser):
		pass

	def check_parameters(self, args):
		pass

	def early_validation(self, path, data):
		pass

	def handle(self, data):

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
