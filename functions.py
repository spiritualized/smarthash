import math, io, os, sys
import cv2
from termcolor import colored, cprint
import magic
import bitstring

from config import blacklist_file_extensions, blacklist_path_matches

def error(msg):
    cprint(msg, 'red')
    sys.exit(1)

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

def listFiles(parent_dir):
    file_list = []
    listFilesInner(parent_dir, None, file_list)

    for x in blacklist_path_matches:
        for file in file_list:
            if x.lower() in file.lower():
                file_list.remove(file)
                continue

    for x in blacklist_file_extensions:
        for file in file_list:
            if file.lower().endswith(x.lower()):
                file_list.remove(file)
                continue

    file_list = [os.path.join(os.path.split(parent_dir)[-1], f) for f in file_list]

    return file_list

def listFilesInner(parent, path, file_list):
    joined_path = os.path.join(parent, path) if path else parent
    for curr in os.scandir(joined_path):
        if curr.is_file():
            file_list.append(os.path.relpath(curr.path, parent))
        elif curr.is_dir():
            listFilesInner(parent, curr.path, file_list)


def prog(amount):
    print('Hashing: %.1f%% complete\r' % (amount * 100), end='\r')


def get_mime_type(path):
    mime_type = ''
    try:
        with open(path, 'rb') as infile:
            return magic.from_buffer(infile.read(1048576), mime=True)
    except:
        pass
    return mime_type

def Mp3Info(path):

    results = {}

    stream = bitstring.ConstBitStream(filename=path)

    # look for Xing
    Xing = stream.find("0x58696E67", bytealigned=True)

    if Xing:
        results['method'] = "VBR"
        stream.bytepos += 4
        xing_flags = stream.read("uint:32")
        if xing_flags & 1:					# skip frames field
            stream.bytepos += 4
        if xing_flags & 2:					# skip bytes field
            stream.bytepos += 4
        if xing_flags & 4:					# skip TOC
            stream.bytepos += 100
        if xing_flags & 8:
            xing_vbr_quality = stream.read("uint:32")
            results['xing_vbr_v'] = 10 - math.ceil(xing_vbr_quality/10)
            results['xing_vbr_q'] = 10 - xing_vbr_quality % 10

        # LAME versions < 3.90 do not contain encoder info, and will not be picked up by this. Treat as VBR
        lame_version = stream.read("bytes:9")
        if lame_version[0:4] == b"LAME":

            # allow for broken/hacked LAME versions, treat as regular VBR
            try:
                results['lame_version'] = lame_version[4:].decode().strip()
                results['lame_tag_revision'] = stream.read("uint:4")
                results['lame_vbr_method'] = stream.read("uint:4")
                stream.bytepos += 9
                results['lame_nspsytune'] = stream.read("bool")
                results['lame_nssafejoint'] = stream.read("bool")
                results['lame_nogap_next'] = stream.read("bool")
                results['lame_nogap_previous'] = stream.read("bool")

                if results['lame_version'][-1] == ".":
                    results['lame_version'] = results['lame_version'][:-1]
            except:
                results['method'] = "VBR"

        return results

    Info = stream.find("0x496E666F", bytealigned=True)
    if Info:
        results['method'] = "CBR"
        return results

    VBRI = stream.find("0x56425249", bytealigned=True)
    if VBRI:
        results['method'] = "VBR"
        return results

    # Assume CBR...
    results['method'] = "CBR"

    return results
