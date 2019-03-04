import os


class TorrentHandler:

	description = "Save a torrent file only"
	options = []

	def attach_arguments(self, argparser):
		pass

	def check_parameters(self, args):
		pass

	def early_validation(self, path, data):
		pass

	def handle(self, data):

		with open(data['save_path'], 'wb') as handle:
			handle.write(data['torrent_file'])
