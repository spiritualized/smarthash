import sys

from termcolor import cprint

from baseplugin import BasePlugin
import os


class SmarthashPlugin(BasePlugin):

	description = "Save a torrent file only"

	def handle(self, data):

		save_path = data['path'] + ".torrent"

		# manual destination
		if data['args'].destination:
			save_path = data['args'].destination

			# if the output path ends with a path seperator
			if save_path.endswith(os.sep):
				save_path += data['title']

			# add a .torrent extension if it's missing
			if not save_path.lower().endswith(".torrent"):
				save_path += ".torrent"

			save_path = os.path.abspath(save_path)

			# check if the output path exists
			if not os.path.isdir(os.path.dirname(save_path)):
				cprint("Output path {0} does not exist".format(os.path.dirname(save_path)), "red")
				sys.exit(1)

		with open(save_path, 'wb') as handle:
			handle.write(data['torrent_file'])
