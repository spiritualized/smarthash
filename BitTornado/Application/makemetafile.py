#pylint: disable=W0102,C0103
import os
import threading
from traceback import print_exc
from typing import List, Dict, Optional

from BitTornado.Meta.BTTree import BTTree
from BitTornado.Meta.Info import MetaInfo

defaults = [
    ('announce-list', '',
        'a list of announce URLs - explained below'),
    ('httpseeds', '',
        'a list of http seed URLs - explained below'),
    ('piece_size_pow2', 0,
        "which power of 2 to set the piece size to (0 = automatic)"),
    ('comment', '',
        "optional human-readable comment to put in .torrent"),
    ('filesystem_encoding', '',
        "optional specification for filesystem encoding " +
        "(set automatically in recent Python versions)"),
    ('target', '',
        "optional target file for the torrent")
]

ignore = ['core', 'CVS']

announcelist_details = \
    """announce-list = optional list of redundant/backup tracker URLs, in the
format:
    url[,url...][|url[,url...]...]
        where URLs separated by commas are all tried first
        before the next group of URLs separated by the pipe is checked.
        If none is given, it is assumed you don't want one in the metafile.
        If announce_list is given, clients which support it
        will ignore the <announce> value.
    Examples:
        http://tracker1.com|http://tracker2.com|http://tracker3.com
            (tries trackers 1-3 in order)
        http://tracker1.com,http://tracker2.com,http://tracker3.com
            (tries trackers 1-3 in a randomly selected order)
        http://tracker1.com|http://backup1.com,http://backup2.com
            (tries tracker 1 first, then tries between the 2 backups randomly)

httpseeds = optional list of http-seed URLs, in the format:
        url[|url...]"""


def is_file_valid(file_obj, params):
    path = [x2.lower() for x2 in file_obj.path]

    # Check if any of the file/foldernames contain a blacklisted word
    for pathsegment in path:
        for match in params['blacklist_path_matches']:
            if match in pathsegment:
                return False

    # Check if the file is on the extension blacklist
    if path[-1].endswith(tuple(params['blacklist_file_extensions'])):
        return False

    return True


def remove_invalid_files(tree: BTTree, params: Dict) -> None:
    """Remove blacklisted files from the metadata tree"""
    to_remove = []
    find_paths_to_remove(tree, params, to_remove)

    for path in to_remove:
        did_remove = remove_invalid_file(tree, path)
        next_path = next_in_file_sequence(path)
        while did_remove and next_path:
            did_remove = remove_invalid_file(tree, next_path)
            next_path = next_in_file_sequence(next_path)


def next_in_file_sequence(path: List[str]) -> Optional[List[str]]:
    """Return the next filename in a logical sequence"""
    parts = path[-1].lower().split('.')
    if len(parts) == 1:
        return None
    name = '.'.join(parts[:-1])
    ext = parts[-1].lower()

    # rar .r00+
    if ext == 'rar':
        return path[:-1] + [f"{name}.r00"]
    elif ext[0] == 'r' and ext[1:].isnumeric():
        num = int(ext[1:]) + 1
        if num == 99:
            return path[:-1] + [f"{name}.000"]
        return path[:-1] + [f"{name}.r{num:02}"]

    # zip .z01+
    elif ext == 'zip':
        return path[:-1] + [f"{name}.z01"]
    elif ext[0] == 'z' and ext[1:].isnumeric():
        num = int(ext[1:]) + 1
        return path[:-1] + [f"{name}.z{num:02}"]

    # multipart .000+
    elif ext.isnumeric():
        num = int(ext) + 1
        if num == 999:
            return None
        return path[:-1] + [f"{name}.{num:03}"]

    return None


def find_paths_to_remove(node: BTTree, params: Dict, marked: List[List[str]]):
    """Create a list of paths to remove"""
    if not node.subs:  # node is a file
        if not is_file_valid(node, params):
            marked.append(node.path)
    else:  # node is a folder
        for sub in node.subs:
            find_paths_to_remove(sub, params, marked)


def remove_invalid_file(node: BTTree, path: List[str]) -> bool:
    """Recurse through the tree and remove the specified path"""
    if not node.subs:  # Should only happen in a single file torrent
        raise ValueError('Single file torrents are not supported')

    for sub in node.subs:
        if not sub.subs and path == sub.path:  # leaf node matched, remove file
            node.subs = [x for x in node.subs if x != sub]
            return True

        if path[0:len(sub.path)] == sub.path:
            if remove_invalid_file(sub, path):  # file was removed further down the recursion chain
                if len(sub.subs) == 0:  # remove empty subdirectory
                    node.subs = [x for x in node.subs if x != sub]
                return True

    return False  # The tree was fully searched, path was not found


def make_meta_file(loc, url, params=None, flag=None,
                   progress=lambda x: None, progress_percent=True):
    """Make a single .torrent file for a given location"""
    if params is None:
        params = {}
    if flag is None:
        flag = threading.Event()

    tree = BTTree(loc, [])

    remove_invalid_files(tree, params)

    # Extract target from parameters
    if 'target' not in params or params['target'] == '':
        fname, ext = os.path.split(loc)
        if ext == '':
            target = fname + '.torrent'
        else:
            target = os.path.join(fname, ext + '.torrent')
        params['target'] = target

    info = tree.makeInfo(flag=flag, progress=progress,
                         progress_percent=progress_percent, **params)

    if flag is not None and flag.is_set():
        return

    metainfo = MetaInfo(info=info, **params)

    return metainfo


def completedir(directory, url, params=None, flag=None,
                progress=lambda x: None, filestat=lambda x: None):
    """Make a .torrent file for each entry in a directory"""
    if params is None:
        params = {}
    if flag is None:
        flag = threading.Event()

    files = sorted(os.listdir(directory))
    ext = '.torrent'

    togen = [os.path.join(directory, fname) for fname in files
             if (fname + ext) not in files and not fname.endswith(ext)]

    trees = [BTTree(loc, []) for loc in togen]

    def subprog(update, subtotal=[0], total=sum(tree.size for tree in trees),
                progress=progress):
        """Aggregate progress callback
        Uses static subtotal to track across files"""
        subtotal[0] += update
        progress(float(subtotal[0]) / total)

    for fname in togen:
        filestat(fname)
        try:
            base = os.path.basename(fname)
            if base not in ignore and base[0] != '.':
                subparams = params.copy()
                if 'target' in params and params['target'] != '':
                    subparams['target'] = os.path.join(params['target'],
                                                       base + ext)
                make_meta_file(fname, url, subparams, flag,
                               progress=subprog, progress_percent=False)
        except ValueError:
            print_exc()
