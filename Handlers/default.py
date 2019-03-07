from basehandler import BaseHandler
import os


class TorrentHandler(BaseHandler):

	description = "Save a torrent file only"

	def handle(self, data):

		with open(data['save_path'], 'wb') as handle:
			handle.write(data['torrent_file'])
