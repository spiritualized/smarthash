import math, io, os
import cv2
from termcolor import colored, cprint

def error(msg):
	cprint(msg, 'red')
	exit(1)

def imgKeyVariance(item):
	return item[1]
def imgKeyOrder(item):
	return item[0]	

def read_nfo(path):
	nfo = None
	try:
		with open(path, "r") as file:
			nfo = file.read()
	except:
		with open(path, "r", encoding="latin-1") as file:
			nfo = file.read()

	return nfo

def choose_genre(genres):
	if len(genres) == 0:
		return None

	ordered_genres = [
						'Sci-Fi',
						'Fantasy',
						'Film Noir',
						'War',
						'Western',
						'Romance',
						'Crime',
						'Horror',
						'Thriller',
						'Mystery',
						'Documentary',
						'Adventure',
						'Action',
						'Comedy',
						'Drama',
						'Sport',
						'Animation',
						'Superhero',
						'Biography',
						'Family',
						'Music',
						'Musical',
						'History',
						'Short',
					]
	for genre in ordered_genres:
		if genre in genres:
			return genre

	return genres[0]


def extractImages(path, n):
	count = 0
	vidcap = cv2.VideoCapture(path)

	n2 = n*2+10
	if n2 < 10:
		n2 = 10

	# take frames at regular intervals from a range excluding the first and last 10% of the file
	frame_count = vidcap.get(cv2.CAP_PROP_FRAME_COUNT)
	frame_count_10 = math.floor(frame_count/10)
	interval = math.floor((frame_count - frame_count_10*2)/(n2+1))

	tmp_images = []
	tmp_variances = []

	for i in range(0, n2):
		print('Extracting images: %.1f%% complete\r' % (i/n2 * 100), end='\r')
		vidcap.set(cv2.CAP_PROP_POS_FRAMES,(frame_count_10 + i*interval))    # added this line 
		success,image = vidcap.read()
		success,buf = cv2.imencode(".jpeg", image)

		variance = cv2.Laplacian(image, cv2.CV_64F).var()
		tmp_images.append(buf.tobytes())
		tmp_variances.append([i, variance])

	# select the N candidates with the highest variance, preserving order
	tmp_variances = sorted(tmp_variances, key=imgKeyVariance, reverse=True)[0:n]
	tmp_variances = sorted(tmp_variances, key=imgKeyOrder)

	images = []
	for x in tmp_variances:
		images.append(tmp_images[x[0]])

	print('Extracting images: %.1f%% complete\r' % (100))

	return images

		#with open("C:\\testhash\\test%d.jpeg" % i, "wb") as file:
		#	file.write()

#	images = sorted()



def prog(amount):
	print('Hashing: %.1f%% complete\r' % (amount * 100), end='\r')

