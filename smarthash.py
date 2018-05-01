import os, sys, importlib, inspect, json, math, re
from collections import OrderedDict

from BitTornado.Application.makemetafile import make_meta_file
from pymediainfo import MediaInfo
from termcolor import colored, cprint

import argparse
import colorama
import magic
import imdb
import mutagen

import MIFormat
from functions import *
from config import *

smarthash_version = "1.0.2"


if __name__ == "__main__":

	colorama.init()

	# list the handler directory for external imports
	handler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Handlers")
	handler_filenames = [f for f in os.listdir(handler_path) if os.path.isfile(os.path.join(handler_path, f))]
	handler_filenames = [ f.split(".")[0] for f in handler_filenames if f.endswith(".py") ]

	# basic parameters
	argparser = argparse.ArgumentParser()
	argparser.add_argument("path")
	argparser.add_argument('--version', action='version', version="SmartHash {0}".format(smarthash_version))
	argparser.add_argument("--handler", help="specify a manual output script: "+", ".join(handler_filenames), default="default")
	argparser.add_argument("--destination", help="specify a file destination")

	handlers = {}

	for x in handler_filenames:
		handlers[x] = importlib.import_module("Handlers."+x)

		if not hasattr(handlers[x], 'handle'):
				print("Could not import \"{0}\" handler".format(x))
				exit()

		# attach handler-specific arguments
		handlers[x].attach_arguments(argparser)

	output_dir = os.getcwd()

	args = argparser.parse_args()

	if args.handler not in handlers:
		print("Invalid handler: {0}".format(args.handler))
		exit()

	handlers[args.handler].check_parameters(args)

	path = os.path.abspath(args.path)


	print("----------------------------\n{0}".format(path))

	# check absolute
	if not os.path.isdir(path):
		cprint("Path does not exist, or is not a directory", 'red')
		exit()

	params = {
				'blacklist_file_extensions': [x.lower() for x in blacklist_file_extensions],
				'blacklist_path_matches': [x.lower() for x in blacklist_path_matches],
				'comment': "Generated with SmartHash {0}".format(smarthash_version),
				'smarthash_version': smarthash_version,
	}

	metainfo = make_meta_file(path, None, params=params, progress=prog)
	print()

	parent_dir = os.path.abspath(os.path.join(path, os.pardir)) + os.path.sep

	formatted_mediainfo = ""
	extracted_images = []
	total_duration = 0

	for file in metainfo['info']['files']:
		file_path = os.path.join(path, *file['path'])
		mime_type = magic.from_file(file_path, mime=True)
		mime_prefix = mime_type.split("/")[0]

		if mime_prefix in ["audio", "video"]:
			smarthash_info = OrderedDict({'mime_type': mime_type})
			smarthash_info['mediainfo'] = []

			media_info = MediaInfo.parse(file_path)
			for track in media_info.tracks:
				track_map = track.to_data()

				# remove the full path for privacy's sake
				if track_map['track_type'] == "General":
					track_map['complete_name'] = track_map['complete_name'].replace(parent_dir, "")
					track_map['folder_name'] = track_map['folder_name'].replace(parent_dir, "")
					total_duration += track_map['duration']

				smarthash_info['mediainfo'].append(track_map)

			# for video files, compose a standard(ish) MediaInfo text output
			if mime_prefix == "video":
				if formatted_mediainfo != "":
					formatted_mediainfo += "\n{0}\n".format("-"*70)
				formatted_mediainfo += MIFormat.MItostring(smarthash_info['mediainfo'])

				if "video-screenshots" in handlers[args.handler].options:
					extracted_images.append(extractImages(file_path, 4))


			# extract audio tags
			elif mime_prefix == "audio":
				smarthash_info['tags'] = OrderedDict()

				mutagen_file = mutagen.File(file_path)	# easy=True

				tags = {}
				for k in mutagen_file:
					# filter out >1500 char (presumably binary) tags, except for comment/lyrics
					if len(str(mutagen_file[k])) < 1500 or k in ["USLT", "COMM"]: 
						tags[k] = str(mutagen_file[k])

				for tag in sorted(tags):
					smarthash_info['tags'][tag] = tags[tag]

			file['smarthash_info'] = json.dumps(smarthash_info)


	data = {	'smarthash_version': smarthash_version,
				'args': args,
				'path': path,
				'title': os.path.split(path)[-1],
				'total_duration': total_duration,
				'mediainfo':formatted_mediainfo,
				'extracted_images':extracted_images,
				'torrent_file': metainfo.gettorrent(),
	}

	# output destination for default handler
	if args.handler == "default":
		data['save_path'] = path + ".torrent"

		# manual destination
		if args.destination:
			data['save_path'] = args.destination

			# if the output path ends with a path seperator
			if data['save_path'].endswith(os.sep):
				data['save_path'] += data['title']

			# add a .torrent extension if it's missing
			if not data['save_path'].lower().endswith(".torrent"):
				data['save_path'] += ".torrent"

			data['save_path'] = os.path.abspath(data['save_path'])
			
			# check if the output path exists
			if not os.path.isdir(os.path.dirname(data['save_path'])):
				cprint("Output path {0} does not exist".format(os.path.dirname(data['save_path'])), "red")
				exit()



	# read nfos
	nfo_filenames = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
	nfo_filenames = [f for f in nfo_filenames if f.lower().endswith(".nfo")]

	nfos = []
	for f in nfo_filenames:
		with open(os.path.join(path, f), "r", encoding="latin-1") as file:
			nfos.append(file.read())

	for nfo in nfos:
		imdb_id = re.findall(r"imdb\.com/title/tt(\d{7})", nfo)
		if imdb_id:
			data['imdb_id'] = imdb_id[0]
			data['nfo'] = nfo

	# default nfo
	if len(nfos) > 0 and 'imdb_id' not in data:
		data['nfo'] = nfos[0]
	else:
		data['nfo'] = ''

	# manual imdb_id override
	if args.imdb_id:
		data['imdb_id'] = args.imdb_id

	# make sure the IMDb ID exists
	if 'imdb_id' in data and 'imdb-id' in handlers[args.handler].options:
		#imdb._logging.setLevel("error")
		print('IMDb querying...\r', end='\r'),
		imdb_site = imdb.IMDb()

		imdb_movie = imdb_site.get_movie(data['imdb_id'])
		if not imdb_movie:
			cprint("Invalid IMDb ID: {0}".format(data['imdb_id']), "red")
			exit()
		print("IMDb verified: \"{0}\"".format(imdb_movie))

		data['genre'] = choose_genre(imdb_movie['genres'])

	handlers[args.handler].handle(data)

	cprint("Done{0}\n".format(" "*40), 'green', end='\r')