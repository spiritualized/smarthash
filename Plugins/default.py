from baseplugin import BasePlugin
import os


class SmarthashPlugin(BasePlugin):

	description = "Save a torrent file only"

	def handle(self, data):

		with open(data['save_path'], 'wb') as handle:
			handle.write(data['torrent_file'])
