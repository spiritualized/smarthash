import hashlib
import random
import bisect
from ..Types import Bitfield, OrderedSet
from BitTornado.clock import clock

DEBUG = False

STATS_INTERVAL = 0.2


def dummy_status(fractionDone=None, activity=None):
    pass


class fakeflag:
    def __init__(self, state=False):
        self.state = state

    def wait(self):
        pass

    def is_set(self):
        return self.state


class StorageWrapper:
    def __init__(self, storage, request_size, hashes, piece_size, finished,
                 failed, statusfunc=dummy_status, flag=fakeflag(),
                 check_hashes=True, data_flunked=lambda x: None, backfunc=None,
                 config={}, unpauseflag=fakeflag(True)):
        self.storage = storage
        self.request_size = int(request_size)
        self.hashes = hashes
        self.piece_size = int(piece_size)
        self.piece_length = int(piece_size)
        self.finished = finished
        self.failed = failed
        self.statusfunc = statusfunc
        self.flag = flag
        self.check_hashes = check_hashes
        self.data_flunked = data_flunked
        self.backfunc = backfunc
        self.config = config
        self.unpauseflag = unpauseflag

        self.alloc_type = config.get('alloc_type', 'normal')
        self.double_check = config.get('double_check', 0)
        self.triple_check = config.get('triple_check', 0)
        if self.triple_check:
            self.double_check = True
        self.bgalloc_enabled = False
        self.bgalloc_active = False
        self.total_length = storage.get_total_length()
        self.amount_left = self.total_length
        if self.total_length <= self.piece_size * (len(hashes) - 1):
            raise ValueError('bad data in responsefile - total too small')
        if self.total_length > self.piece_size * len(hashes):
            raise ValueError('bad data in responsefile - total too big')
        self.numactive = [0] * len(hashes)
        self.inactive_requests = [1] * len(hashes)
        self.amount_inactive = self.total_length
        self.amount_obtained = 0
        self.amount_desired = self.total_length
        self.have = Bitfield(len(hashes))
        self.have_cloaked_data = None
        self.blocked = [False] * len(hashes)
        self.blocked_holes = []
        self.blocked_movein = OrderedSet()
        self.blocked_moveout = OrderedSet()
        self.waschecked = [False] * len(hashes)
        self.places = {}
        self.holes = []
        self.stat_active = set()
        self.stat_new = set()
        self.dirty = {}
        self.stat_numflunked = 0
        self.stat_numdownloaded = 0
        self.stat_numfound = 0
        self.download_history = {}
        self.failed_pieces = {}
        self.out_of_place = 0
        self.write_buf_max = config['write_buffer_size'] * 1048576
        self.write_buf_size = 0
        self.write_buf = {}   # structure:  piece: [(start, data), ...]
        self.write_buf_list = []

        self.initialize_tasks = [
            ['checking existing data', 0, self.init_hashcheck,
             self.hashcheckfunc],
            ['moving data', 1, self.init_movedata, self.movedatafunc],
            ['allocating disk space', 1, self.init_alloc, self.allocfunc]]

        self.backfunc(self._bgalloc, 0.1)
        self.backfunc(self._bgsync, max(self.config['auto_flush'] * 60, 60))

    def _bgsync(self):
        if self.config['auto_flush']:
            self.sync()
        self.backfunc(self._bgsync, max(self.config['auto_flush'] * 60, 60))

    def old_style_init(self):
        while self.initialize_tasks:
            msg, done, init, next = self.initialize_tasks.pop(0)
            if init():
                self.statusfunc(activity=msg, fractionDone=done)
                t = clock() + STATS_INTERVAL
                x = 0
                while x is not None:
                    if t < clock():
                        t = clock() + STATS_INTERVAL
                        self.statusfunc(fractionDone=x)
                    self.unpauseflag.wait()
                    if self.flag.is_set():
                        return False
                    x = next()

        self.statusfunc(fractionDone=0)
        return True

    def initialize(self, donefunc, statusfunc=None):
        self.initialize_done = donefunc
        if statusfunc is None:
            statusfunc = self.statusfunc
        self.initialize_status = statusfunc
        self.initialize_next = None

        self.backfunc(self._initialize)

    def _initialize(self):
        if not self.unpauseflag.is_set():
            self.backfunc(self._initialize, 1)
            return

        if self.initialize_next:
            x = self.initialize_next()
            if x is None:
                self.initialize_next = None
            else:
                self.initialize_status(fractionDone=x)
        else:
            if not self.initialize_tasks:
                self.initialize_done()
                return
            msg, done, init, next = self.initialize_tasks.pop(0)
            if init():
                self.initialize_status(activity=msg, fractionDone=done)
                self.initialize_next = next

        self.backfunc(self._initialize)

    def init_hashcheck(self):
        if self.flag.is_set():
            return False
        self.check_list = []
        if len(self.hashes) == 0 or self.amount_left == 0:
            self.check_total = 0
            self.finished()
            return False

        self.check_targets = {}
        got = set()
        for v in self.places.values():
            assert v not in got
            got.add(v)
        for i, hval in enumerate(self.hashes):
            if i in self.places:  # restored from pickled
                self.check_targets[hval] = []
                if self.places[i] == i:
                    continue
                else:
                    assert i not in got
                    self.out_of_place += 1
            if i in got:
                continue
            if self._waspre(i):
                if self.blocked[i]:
                    self.places[i] = i
                else:
                    self.check_list.append(i)
                continue
            if not self.check_hashes:
                self.failed('told file complete on start-up, but data is '
                            'missing')
                return False
            self.holes.append(i)
            if self.blocked[i] or hval in self.check_targets:
                # in case of a hash collision, discard
                self.check_targets[hval] = []
            else:
                self.check_targets[hval] = [i]
        self.check_total = len(self.check_list)
        self.check_numchecked = 0.0
        self.lastlen = self._piecelen(len(self.hashes) - 1)
        self.numchecked = 0.0
        return self.check_total > 0

    def _markgot(self, piece, pos):
        if DEBUG:
            print(piece, ' at ', pos)
        self.places[piece] = pos
        self.have[piece] = True
        len = self._piecelen(piece)
        self.amount_obtained += len
        self.amount_left -= len
        self.amount_inactive -= len
        self.inactive_requests[piece] = None
        self.waschecked[piece] = self.check_hashes
        self.stat_numfound += 1

    def hashcheckfunc(self):
        if self.flag.is_set():
            return None
        if not self.check_list:
            return None

        i = self.check_list.pop(0)
        if not self.check_hashes:
            self._markgot(i, i)
        else:
            d1 = self.read_raw(i, 0, self.lastlen)
            if d1 is None:
                return None
            sh = hashlib.sha1(d1[:])
            d1.release()
            sp = sh.digest()
            d2 = self.read_raw(i, self.lastlen,
                               self._piecelen(i) - self.lastlen)
            if d2 is None:
                return None
            sh.update(d2[:])
            d2.release()
            s = sh.digest()
            if s == self.hashes[i]:
                self._markgot(i, i)
            elif self.check_targets.get(s) and self._piecelen(i) == \
                    self._piecelen(self.check_targets[s][-1]):
                self._markgot(self.check_targets[s].pop(), i)
                self.out_of_place += 1
            elif not self.have[-1] and sp == self.hashes[-1] and (
                    i == len(self.hashes) - 1 or
                    not self._waspre(len(self.hashes) - 1)):
                self._markgot(len(self.hashes) - 1, i)
                self.out_of_place += 1
            else:
                self.places[i] = i
        self.numchecked += 1
        if self.amount_left == 0:
            self.finished()
        return self.numchecked / self.check_total

    def init_movedata(self):
        if self.flag.is_set():
            return False
        if self.alloc_type != 'sparse':
            return False
        self.storage.top_off()  # sets file lengths to their final size
        self.movelist = []
        if self.out_of_place == 0:
            for i in self.holes:
                self.places[i] = i
            self.holes = []
            return False
        self.tomove = float(self.out_of_place)
        for i in range(len(self.hashes)):
            if i not in self.places:
                self.places[i] = i
            elif self.places[i] != i:
                self.movelist.append(i)
        self.holes = []
        return True

    def movedatafunc(self):
        if self.flag.is_set():
            return None
        if not self.movelist:
            return None
        i = self.movelist.pop(0)
        old = self.read_raw(self.places[i], 0, self._piecelen(i))
        if old is None:
            return None
        if not self.write_raw(i, 0, old):
            return None
        if self.double_check and self.have[i]:
            if self.triple_check:
                old.release()
                old = self.read_raw(i, 0, self._piecelen(i), flush_first=True)
                if old is None:
                    return None
            if hashlib.sha1(old[:]).digest() != self.hashes[i]:
                self.failed('download corrupted; please restart and resume')
                return None
        old.release()

        self.places[i] = i
        self.tomove -= 1
        return self.tomove / self.out_of_place

    def init_alloc(self):
        if self.flag.is_set():
            return False
        if not self.holes:
            return False
        self.numholes = float(len(self.holes))
        self.alloc_buf = b'\xff' * self.piece_size
        if self.alloc_type == 'pre-allocate':
            self.bgalloc_enabled = True
            return True
        if self.alloc_type == 'background':
            self.bgalloc_enabled = True
        if self.blocked_moveout:
            return True
        return False

    def _allocfunc(self):
        while self.holes:
            n = self.holes.pop(0)
            if self.blocked[n]:     # assume not self.blocked[index]
                if not self.blocked_movein:
                    self.blocked_holes.append(n)
                    continue
                if n not in self.places:
                    b = self.blocked_movein.pop(0)
                    oldpos = self._move_piece(b, n)
                    self.places[oldpos] = oldpos
                    return None
            if n in self.places:
                oldpos = self._move_piece(n, n)
                self.places[oldpos] = oldpos
                return None
            return n
        return None

    def allocfunc(self):
        if self.flag.is_set():
            return None

        if self.blocked_moveout:
            self.bgalloc_active = True
            n = self._allocfunc()
            if n is not None:
                if n in self.blocked_moveout:
                    self.blocked_moveout.remove(n)
                    b = n
                else:
                    b = self.blocked_moveout.pop()
                oldpos = self._move_piece(b, n)
                self.places[oldpos] = oldpos
            return len(self.holes) / self.numholes

        if self.holes and self.bgalloc_enabled:
            self.bgalloc_active = True
            n = self._allocfunc()
            if n is not None:
                self.write_raw(n, 0, self.alloc_buf[:self._piecelen(n)])
                self.places[n] = n
            return len(self.holes) / self.numholes

        self.bgalloc_active = False
        return None

    def bgalloc(self):
        if self.bgalloc_enabled:
            if not self.holes and not self.blocked_moveout and self.backfunc:
                self.backfunc(self.storage.flush)
                # force a flush whenever the "finish allocation" button is hit
        self.bgalloc_enabled = True
        return False

    def _bgalloc(self):
        self.allocfunc()
        if self.config.get('alloc_rate', 0) < 0.1:
            self.config['alloc_rate'] = 0.1
        self.backfunc(self._bgalloc, float(self.piece_size) /
                      (self.config['alloc_rate'] * 1048576))

    def _waspre(self, piece):
        return self.storage.was_preallocated(piece * self.piece_size,
                                             self._piecelen(piece))

    def _piecelen(self, piece):
        if piece < len(self.hashes) - 1:
            return self.piece_size
        else:
            return self.total_length - (piece * self.piece_size)

    def get_amount_left(self):
        return self.amount_left

    def do_I_have_anything(self):
        return self.amount_left < self.total_length

    def _make_inactive(self, index):
        length = self._piecelen(index)
        l = []
        x = 0
        while x + self.request_size < length:
            l.append((x, self.request_size))
            x += self.request_size
        l.append((x, length - x))
        self.inactive_requests[index] = l

    def is_endgame(self):
        return not self.amount_inactive

    def am_I_complete(self):
        return self.amount_obtained == self.amount_desired

    def reset_endgame(self, requestlist):
        for index, begin, length in requestlist:
            self.request_lost(index, begin, length)

    def get_have_list(self):
        return bytes(self.have)

    def get_have_list_cloaked(self):
        if self.have_cloaked_data is None:
            newhave = Bitfield(copyfrom=self.have)
            unhaves = []
            # between 2-4 unless torrent is small
            n = min(random.randrange(2, 5), len(self.hashes))
            while len(unhaves) < n:
                # all in first 4 bytes
                unhave = random.randrange(min(32, len(self.hashes)))
                if unhave not in unhaves:
                    unhaves.append(unhave)
                    newhave[unhave] = False
            self.have_cloaked_data = (bytes(newhave), unhaves)
        return self.have_cloaked_data

    def do_I_have(self, index):
        return self.have[index]

    def do_I_have_requests(self, index):
        return not not self.inactive_requests[index]

    def is_unstarted(self, index):
        return not self.have[index] and not self.numactive[index] and \
            index not in self.dirty

    def get_hash(self, index):
        return self.hashes[index]

    def get_stats(self):
        return self.amount_obtained, self.amount_desired

    def new_request(self, index):
        # returns (begin, length)
        if self.inactive_requests[index] == 1:
            self._make_inactive(index)
        self.numactive[index] += 1
        self.stat_active.add(index)
        if index not in self.dirty:
            self.stat_new.add(index)
        rs = self.inactive_requests[index]
#        r = min(rs)
#        rs.remove(r)
        r = rs.pop(0)
        self.amount_inactive -= r[1]
        return r

    def write_raw(self, index, begin, data):
        try:
            self.storage.write(self.piece_size * index + begin, data)
            return True
        except IOError as e:
            self.failed('IO Error: ' + str(e))
            return False

    def _write_to_buffer(self, piece, start, data):
        if not self.write_buf_max:
            return self.write_raw(self.places[piece], start, data)
        self.write_buf_size += len(data)
        while self.write_buf_size > self.write_buf_max:
            old = self.write_buf_list.pop(0)
            if not self._flush_buffer(old, True):
                return False
        if piece in self.write_buf:
            self.write_buf_list.remove(piece)
        else:
            self.write_buf[piece] = []
        self.write_buf_list.append(piece)
        self.write_buf[piece].append((start, data))
        return True

    def _flush_buffer(self, piece, popped=False):
        if piece not in self.write_buf:
            return True
        if not popped:
            self.write_buf_list.remove(piece)
        l = self.write_buf[piece]
        del self.write_buf[piece]
        l.sort()
        for start, data in l:
            self.write_buf_size -= len(data)
            if not self.write_raw(self.places[piece], start, data):
                return False
        return True

    def sync(self):
        # No clear reason for these to be in a dictionary and sorted by their
        # entries in self.places, but that's how it came
        spots = {self.places[p]: p for p in self.write_buf_list}
        for _, write_buf in sorted(spots.items()):
            try:
                self._flush_buffer(write_buf)
            except IOError:
                pass
        try:
            self.storage.sync()
        except IOError as e:
            self.failed('IO Error: ' + str(e))
        except OSError as e:
            self.failed('OS Error: ' + str(e))

    def _move_piece(self, index, newpos):
        oldpos = self.places[index]
        if DEBUG:
            print('moving {} from {} to {}'.format(index, oldpos, newpos))
        assert oldpos != index
        assert oldpos != newpos
        assert index == newpos or newpos not in self.places
        old = self.read_raw(oldpos, 0, self._piecelen(index))
        if old is None:
            return -1
        if not self.write_raw(newpos, 0, old):
            return -1
        self.places[index] = newpos
        if self.have[index] and (
                self.triple_check or self.double_check and index == newpos):
            if self.triple_check:
                old.release()
                old = self.read_raw(newpos, 0, self._piecelen(index),
                                    flush_first=True)
                if old is None:
                    return -1
            if hashlib.sha1(old[:]).digest() != self.hashes[index]:
                self.failed('download corrupted; please restart and resume')
                return -1
        old.release()

        if self.blocked[index]:
            self.blocked_moveout.discard(index)
            if self.blocked[newpos]:
                self.blocked_movein.discard(index)
            else:
                self.blocked_movein.add(index)
        else:
            self.blocked_movein.discard(index)
            if self.blocked[newpos]:
                self.blocked_moveout.add(index)
            else:
                self.blocked_moveout.discard(index)

        return oldpos

    def _clear_space(self, index):
        h = self.holes.pop(0)
        n = h
        if self.blocked[n]:     # assume not self.blocked[index]
            if not self.blocked_movein:
                self.blocked_holes.append(n)
                return True    # repeat
            if n not in self.places:
                b = self.blocked_movein.pop(0)
                oldpos = self._move_piece(b, n)
                if oldpos < 0:
                    return False
                n = oldpos
        if n in self.places:
            oldpos = self._move_piece(n, n)
            if oldpos < 0:
                return False
            n = oldpos
        if index == n or index in self.holes:
            if n == h:
                self.write_raw(n, 0, self.alloc_buf[:self._piecelen(n)])
            self.places[index] = n
            if self.blocked[n]:
                # because n may be a spot cleared 10 lines above, it's possible
                # for it to be blocked.  While that spot could be left cleared
                # and a new spot allocated, this condition might occur several
                # times in a row, resulting in a significant amount of disk
                # I/O, # delaying the operation of the engine.  Rather than do
                # this, queue the piece to be moved out again, which will be
                # performed by the background allocator, with which data
                # movement is automatically limited.
                self.blocked_moveout.add(index)
            return False
        for p, v in self.places.items():
            if v == index:
                break
        else:
            self.failed('download corrupted; please restart and resume')
            return False
        self._move_piece(p, n)
        self.places[index] = index
        return False

    def piece_came_in(self, index, begin, piece, source=None):
        assert not self.have[index]

        if index not in self.places:
            while self._clear_space(index):
                pass
            if DEBUG:
                print('new place for {} at {}'.format(index,
                                                      self.places[index]))
        if self.flag.is_set():
            return

        if index in self.failed_pieces:
            old = self.read_raw(self.places[index], begin, len(piece))
            if old is None:
                return True
            if old[:].tostring() != piece:
                try:
                    self.failed_pieces[index].add(
                        self.download_history[index][begin])
                except KeyError:
                    self.failed_pieces[index].add(None)
            old.release()
        self.download_history.setdefault(index, {})[begin] = source

        if not self._write_to_buffer(index, begin, piece):
            return True

        self.amount_obtained += len(piece)
        self.dirty.setdefault(index, []).append((begin, len(piece)))
        self.numactive[index] -= 1
        assert self.numactive[index] >= 0
        if not self.numactive[index]:
            self.stat_active.discard(index)
        self.stat_new.discard(index)

        if self.inactive_requests[index] or self.numactive[index]:
            return True

        del self.dirty[index]
        if not self._flush_buffer(index):
            return True
        length = self._piecelen(index)
        data = self.read_raw(self.places[index], 0, length,
                             flush_first=self.triple_check)
        if data is None:
            return True
        hash = hashlib.sha1(data[:]).digest()
        data.release()
        if hash != self.hashes[index]:

            self.amount_obtained -= length
            self.data_flunked(length, index)
            self.inactive_requests[index] = 1
            self.amount_inactive += length
            self.stat_numflunked += 1

            self.failed_pieces[index] = set()
            allsenders = set(self.download_history[index].values())
            if len(allsenders) == 1:
                culprit = allsenders.pop()
                if culprit is not None:
                    culprit.failed(index, bump=True)
                del self.failed_pieces[index]   # found the culprit already

            return False

        self.have[index] = True
        self.inactive_requests[index] = None
        self.waschecked[index] = True
        self.amount_left -= length
        self.stat_numdownloaded += 1

        for d in self.download_history[index].values():
            if d is not None:
                d.good(index)
        del self.download_history[index]
        if index in self.failed_pieces:
            for d in self.failed_pieces[index]:
                if d is not None:
                    d.failed(index)
            del self.failed_pieces[index]

        if self.amount_left == 0:
            self.finished()
        return True

    def request_lost(self, index, begin, length):
        assert not (begin, length) in self.inactive_requests[index]
        bisect.insort(self.inactive_requests[index], (begin, length))
        self.amount_inactive += length
        self.numactive[index] -= 1
        if not self.numactive[index]:
            self.stat_active.discard(index)
            self.stat_new.discard(index)

    def get_piece(self, index, begin, length):
        if not self.have[index]:
            return None
        data = None
        if not self.waschecked[index]:
            data = self.read_raw(self.places[index], 0, self._piecelen(index))
            if data is None:
                return None
            if hashlib.sha1(data[:]).digest() != self.hashes[index]:
                self.failed('told file complete on start-up, but piece failed '
                            'hash check')
                return None
            self.waschecked[index] = True
            if length == -1 and begin == 0:
                return data     # optimization
        if length == -1:
            if begin > self._piecelen(index):
                return None
            length = self._piecelen(index) - begin
            if begin == 0:
                return self.read_raw(self.places[index], 0, length)
        elif begin + length > self._piecelen(index):
            return None
        if data is not None:
            s = data[begin:begin + length]
            data.release()
            return s
        data = self.read_raw(self.places[index], begin, length)
        if data is None:
            return None
        s = data.getarray()
        data.release()
        return s

    def read_raw(self, piece, begin, length, flush_first=False):
        try:
            return self.storage.read(self.piece_size * piece + begin,
                                     length, flush_first)
        except IOError as e:
            self.failed('IO Error: ' + str(e))
            return None

    def set_file_readonly(self, n):
        try:
            self.storage.set_readonly(n)
        except IOError as e:
            self.failed('IO Error: ' + str(e))
        except OSError as e:
            self.failed('OS Error: ' + str(e))

    def has_data(self, index):
        return index not in self.holes and index not in self.blocked_holes

    def doublecheck_data(self, pieces_to_check):
        if not self.double_check:
            return
        sources = []
        for p, v in self.places.items():
            if v in pieces_to_check:
                sources.append(p)
        assert len(sources) == len(pieces_to_check)
        sources.sort()
        for index in sources:
            if self.have[index]:
                piece = self.read_raw(self.places[index], 0,
                                      self._piecelen(index), flush_first=True)
                if piece is None:
                    return False
                if hashlib.sha1(piece[:]).digest() != self.hashes[index]:
                    self.failed('download corrupted; please restart and '
                                'resume')
                    return False
                piece.release()
        return True

    def reblock(self, new_blocked):
        # assume downloads have already been canceled and chunks made inactive
        for i, nblock in enumerate(new_blocked):
            if nblock and not self.blocked[i]:
                length = self._piecelen(i)
                self.amount_desired -= length
                if self.have[i]:
                    self.amount_obtained -= length
                    continue
                if self.inactive_requests[i] == 1:
                    self.amount_inactive -= length
                    continue
                inactive = 0
                for _, nl in self.inactive_requests[i]:
                    inactive += nl
                self.amount_inactive -= inactive
                self.amount_obtained -= length - inactive

            if self.blocked[i] and not nblock:
                length = self._piecelen(i)
                self.amount_desired += length
                if self.have[i]:
                    self.amount_obtained += length
                    continue
                if self.inactive_requests[i] == 1:
                    self.amount_inactive += length
                    continue
                inactive = 0
                for _, nl in self.inactive_requests[i]:
                    inactive += nl
                self.amount_inactive += inactive
                self.amount_obtained += length - inactive

        self.blocked = new_blocked

        self.blocked_movein = OrderedSet()
        self.blocked_moveout = OrderedSet()
        for p, v in self.places.items():
            if p != v:
                if self.blocked[p] and not self.blocked[v]:
                    self.blocked_movein.add(p)
                elif self.blocked[v] and not self.blocked[p]:
                    self.blocked_moveout.add(p)

        self.holes.extend(self.blocked_holes)    # reset holes list
        self.holes.sort()
        self.blocked_holes = []

    '''
    Pickled data format:

    d['pieces'] = either a string containing a bitfield of complete pieces,
                    or the numeric value "1" signifying a seed.  If it is
                    a seed, d['places'] and d['partials'] should be empty
                    and needn't even exist.
    d['partials'] = [ piece, [ offset, length... ]... ]
                    a list of partial data that had been previously
                    downloaded, plus the given offsets.  Adjacent partials
                    are merged so as to save space, and so that if the
                    request size changes then new requests can be
                    calculated more efficiently.
    d['places'] = [ piece, place, {, piece, place ...} ]
                    the piece index, and the place it's stored.
                    If d['pieces'] specifies a complete piece or d['partials']
                    specifies a set of partials for a piece which has no
                    entry in d['places'], it can be assumed that
                    place[index] = index.  A place specified with no
                    corresponding data in d['pieces'] or d['partials']
                    indicates allocated space with no valid data, and is
                    reserved so it doesn't need to be hash-checked.
    '''
    def pickle(self):
        if self.have.complete:
            return {'pieces': 1}
        pieces = Bitfield(len(self.hashes))
        places = []
        partials = []
        for p in range(len(self.hashes)):
            if self.blocked[p] or p not in self.places:
                continue
            h = self.have[p]
            pieces[p] = h
            pp = self.dirty.get(p)
            if not h and not pp:  # no data
                places.extend([self.places[p], self.places[p]])
            elif self.places[p] != p:
                places.extend([p, self.places[p]])
            if h or not pp:
                continue
            pp.sort()
            r = []
            while len(pp) > 1:
                if pp[0][0] + pp[0][1] == pp[1][0]:
                    pp[0] = (pp[0][0], pp[0][1] + pp[1][1])
                    del pp[1]
                else:
                    r.extend(pp[0])
                    del pp[0]
            r.extend(pp[0])
            partials.extend([p, r])
        return {'pieces': bytes(pieces), 'places': places,
                'partials': partials}

    def unpickle(self, data, valid_places):
        got = set()
        places = {}
        dirty = {}
        download_history = {}
        stat_active = set()
        stat_numfound = self.stat_numfound
        amount_obtained = self.amount_obtained
        amount_inactive = self.amount_inactive
        amount_left = self.amount_left
        inactive_requests = [x for x in self.inactive_requests]
        restored_partials = []

        try:
            if data['pieces'] == 1:     # a seed
                assert not data.get('places', None)
                assert not data.get('partials', None)
                have = Bitfield(len(self.hashes), val=True)
                assert have.complete
                _places = []
                _partials = []
            else:
                have = Bitfield(len(self.hashes), data['pieces'])
                _places = data['places']
                assert len(_places) % 2 == 0
                _places = [_places[x:x + 2]
                           for x in range(0, len(_places), 2)]
                _partials = data['partials']
                assert len(_partials) % 2 == 0
                _partials = [_partials[x:x + 2]
                             for x in range(0, len(_partials), 2)]

            for index, place in _places:
                if place not in valid_places:
                    continue
                assert index not in got
                assert place not in got
                places[index] = place
                got.add(index)
                got.add(place)

            for index in range(len(self.hashes)):
                if have[index]:
                    if index not in places:
                        if index not in valid_places:
                            have[index] = False
                            continue
                        assert index not in got
                        places[index] = index
                        got.add(index)
                    length = self._piecelen(index)
                    amount_obtained += length
                    stat_numfound += 1
                    amount_inactive -= length
                    amount_left -= length
                    inactive_requests[index] = None

            for index, plist in _partials:
                assert index not in dirty
                assert not have[index]
                if index not in places:
                    if index not in valid_places:
                        continue
                    assert index not in got
                    places[index] = index
                    got.add(index)
                assert len(plist) % 2 == 0
                plist = [tuple(plist[x:x + 2])
                         for x in range(0, len(plist), 2)]
                dirty[index] = plist
                stat_active.add(index)
                download_history[index] = {}
                # invert given partials
                length = self._piecelen(index)
                l = []
                if plist[0][0] > 0:
                    l.append((0, plist[0][0]))

                for pieceA, pieceB in zip(plist[:-1], plist[1:]):
                    end = pieceA[0] + pieceA[1]
                    assert not end > pieceB[0]
                    l.append((end, pieceB[0] - end))
                end = pieceB[0] + pieceB[1]
                assert not end > length

                if end < length:
                    l.append((end, length - end))
                # split them to request_size
                ll = []
                amount_obtained += length
                amount_inactive -= length
                for nb, nl in l:
                    while nl > 0:
                        r = min(nl, self.request_size)
                        ll.append((nb, r))
                        amount_inactive += r
                        amount_obtained -= r
                        nb += self.request_size
                        nl -= self.request_size
                inactive_requests[index] = ll
                restored_partials.append(index)

            assert amount_obtained + amount_inactive == self.amount_desired
        except Exception:
            # print_exc()
            return []   # invalid data, discard everything

        self.have = have
        self.places = places
        self.dirty = dirty
        self.download_history = download_history
        self.stat_active = stat_active
        self.stat_numfound = stat_numfound
        self.amount_obtained = amount_obtained
        self.amount_inactive = amount_inactive
        self.amount_left = amount_left
        self.inactive_requests = inactive_requests

        return restored_partials
