import os


description = "Save a torrent file only"
options = []

def attach_arguments(argparser):
	pass

def check_parameters(args):
	pass

def handle(data):

	with open(data['save_path'], 'wb') as handle:
		handle.write(data['torrent_file'])
