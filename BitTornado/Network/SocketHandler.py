import time
import socket
import random
from errno import EWOULDBLOCK
try:
    from select import poll, POLLIN, POLLOUT, POLLERR, POLLHUP
except ImportError:
    from .selectpoll import poll, POLLIN, POLLOUT, POLLERR, POLLHUP
from BitTornado.clock import clock
from .natpunch import UPnP_open_port, UPnP_close_port

POLLALL = POLLIN | POLLOUT

UPnP_ERROR = "unable to forward port via UPnP"


class SingleSocket(object):
    def __init__(self, socket_handler, sock, handler, ip=None):
        self.socket_handler = socket_handler
        self.socket = sock
        self.handler = handler
        self.buffer = []
        self.last_hit = clock()
        self.fileno = sock.fileno()
        self.connected = False
        self.skipped = 0
        try:
            self.ip = self.socket.getpeername()[0]
        except OSError:
            if ip is None:
                self.ip = 'unknown'
            else:
                self.ip = ip

    def get_ip(self, real=False):
        if real:
            try:
                self.ip = self.socket.getpeername()[0]
            except OSError:
                pass
        return self.ip

    def close(self):
        '''
        for x in xrange(5,0,-1):
            try:
                f = inspect.currentframe(x).f_code
                print (f.co_filename,f.co_firstlineno,f.co_name)
                del f
            except:
                pass
        print ''
        '''
        assert self.socket
        self.connected = False
        sock = self.socket
        self.socket = None
        self.buffer = []
        del self.socket_handler.single_sockets[self.fileno]
        self.socket_handler.poll.unregister(sock)
        sock.close()

    def shutdown(self, val):
        try:
            self.socket.shutdown(val)
        except OSError:
            pass

    def is_flushed(self):
        return not self.buffer

    def write(self, s):
        # self.check.write(s)
        assert self.socket is not None
        self.buffer.append(s)
        if len(self.buffer) == 1:
            self.try_write()

    def try_write(self):
        if self.connected:
            dead = False
            try:
                while self.buffer:
                    buf = self.buffer[0]
                    amount = self.socket.send(buf)
                    if amount == 0:
                        self.skipped += 1
                        break
                    self.skipped = 0
                    if amount != len(buf):
                        self.buffer[0] = buf[amount:]
                        break
                    del self.buffer[0]
            except OSError as e:
                try:
                    dead = e.errno != EWOULDBLOCK
                except Exception:
                    dead = True
                self.skipped += 1
            if self.skipped >= 3:
                dead = True
            if dead:
                self.socket_handler.dead_from_write.append(self)
                return
        if self.buffer:
            self.socket_handler.poll.register(self.socket, POLLALL)
        else:
            self.socket_handler.poll.register(self.socket, POLLIN)

    def set_handler(self, handler):
        self.handler = handler


class SocketHandler(object):
    def __init__(self, timeout, ipv6_enable, readsize=100000):
        self.timeout = timeout
        self.ipv6_enable = ipv6_enable
        self.readsize = readsize
        self.poll = poll()
        self.single_sockets = {}  # {socket: SingleSocket}
        self.dead_from_write = []
        self.max_connects = 1000
        self.port_forwarded = None
        self.servers = {}

    def scan_for_timeouts(self):
        t = clock() - self.timeout
        for s in list(self.single_sockets.values()):
            if s.last_hit < t and s.socket is not None:
                self._close_socket(s)

    def bind(self, port, bind='', reuse=False, ipv6_socket_style=1, upnp=0):
        port = int(port)
        addrinfos = []
        self.servers = {}
        self.interfaces = []
        # if bind != "" thread it as a comma seperated list and bind to all
        # addresses (can be ips or hostnames) else bind to default ipv6 and
        # ipv4 address
        if bind:
            if self.ipv6_enable:
                socktype = socket.AF_UNSPEC
            else:
                socktype = socket.AF_INET
            for addr in bind.split(','):
                addrinfos.extend(socket.getaddrinfo(addr, port,
                                 socktype, socket.SOCK_STREAM))
        else:
            if self.ipv6_enable:
                addrinfos.append([socket.AF_INET6, None, None, None,
                                 ('', port)])
            if not addrinfos or ipv6_socket_style != 0:
                addrinfos.append([socket.AF_INET, None, None, None,
                                 ('', port)])
        for addrinfo in addrinfos:
            try:
                server = socket.socket(addrinfo[0], socket.SOCK_STREAM)
                if reuse:
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,
                                      1)
                server.setblocking(0)
                server.bind(addrinfo[4])
                self.servers[server.fileno()] = server
                if bind:
                    self.interfaces.append(server.getsockname()[0])
                server.listen(64)
                self.poll.register(server, POLLIN)
            except OSError as e:
                # servers is a dict of sockets, so there's no danger of
                # altering self.servers in this loop
                for server in self.servers.values():
                    try:
                        server.close()
                    except OSError:
                        pass
                if self.ipv6_enable and ipv6_socket_style == 0 and \
                        self.servers:
                    raise OSError(
                        'blocked port (may require ipv6_binds_v4 to be set)')
                raise e
        if not self.servers:
            raise OSError('unable to open server port')
        if upnp:
            if not UPnP_open_port(port):
                # servers is a dict of sockets, so there's no danger of
                # altering self.servers in this loop
                for server in self.servers.values():
                    try:
                        server.close()
                    except OSError:
                        pass
                self.servers = None
                self.interfaces = None
                raise OSError(UPnP_ERROR)
            self.port_forwarded = port
        self.port = port

    def find_and_bind(self, minport, maxport, bind='', reuse=False,
                      ipv6_socket_style=1, upnp=0, randomizer=False):
        e = 'maxport less than minport - no ports to check'
        # Check a maximum of 20 ports
        nports = max(maxport - minport, 20)
        portrange = random.sample(range(minport, maxport + 1), nports) \
            if randomizer else range(minport, minport + nports)
        for listen_port in portrange:
            try:
                self.bind(listen_port, bind,
                          ipv6_socket_style=ipv6_socket_style, upnp=upnp)
                return listen_port
            except OSError as e:
                pass
        raise OSError(str(e))

    def set_handler(self, handler):
        self.handler = handler

    def start_connection_raw(self, dns, socktype=socket.AF_INET, handler=None):
        if handler is None:
            handler = self.handler
        sock = socket.socket(socktype, socket.SOCK_STREAM)
        sock.setblocking(0)
        try:
            sock.connect_ex(dns)
        except OSError:
            raise
        except Exception as e:
            raise OSError(str(e))
        self.poll.register(sock, POLLIN)
        s = SingleSocket(self, sock, handler, dns[0])
        self.single_sockets[sock.fileno()] = s
        return s

    def start_connection(self, dns, handler=None, randomize=False):
        if handler is None:
            handler = self.handler

        if self.ipv6_enable:
            socktype = socket.AF_UNSPEC
        else:
            socktype = socket.AF_INET
        try:
            addrinfos = socket.getaddrinfo(dns[0], int(dns[1]),
                                           socktype, socket.SOCK_STREAM)
        except OSError as e:
            raise
        except Exception as e:
            raise OSError(str(e))
        if randomize:
            random.shuffle(addrinfos)
        for addrinfo in addrinfos:
            try:
                s = self.start_connection_raw(addrinfo[4], addrinfo[0],
                                              handler)
                break
            except OSError:
                pass
        else:
            raise OSError('unable to connect')

        return s

    def handle_events(self, events):
        for sock, event in events:
            s = self.servers.get(sock)
            if s:
                if event & (POLLHUP | POLLERR) != 0:
                    self.poll.unregister(s)
                    s.close()
                    del self.servers[sock]
                    print("lost server socket")
                elif len(self.single_sockets) < self.max_connects:
                    try:
                        newsock, _ = s.accept()
                        newsock.setblocking(0)
                        nss = SingleSocket(self, newsock, self.handler)
                        self.single_sockets[newsock.fileno()] = nss
                        self.poll.register(newsock, POLLIN)
                        self.handler.external_connection_made(nss)
                    except OSError:
                        time.sleep(1)
            else:
                s = self.single_sockets.get(sock)
                if not s:
                    continue
                s.connected = True
                if event & (POLLHUP | POLLERR):
                    self._close_socket(s)
                    continue
                if event & POLLIN:
                    try:
                        s.last_hit = clock()
                        data = s.socket.recv(self.readsize)
                        if not data:
                            self._close_socket(s)
                        else:
                            s.handler.data_came_in(s, data)
                    except OSError as e:
                        if e.errno != EWOULDBLOCK:
                            self._close_socket(s)
                            continue
                if event & POLLOUT and s.socket and not s.is_flushed():
                    s.try_write()
                    if s.is_flushed():
                        s.handler.connection_flushed(s)

    def close_dead(self):
        while self.dead_from_write:
            old = self.dead_from_write
            self.dead_from_write = []
            for s in old:
                if s.socket:
                    self._close_socket(s)

    def _close_socket(self, s):
        s.close()
        s.handler.connection_lost(s)

    def do_poll(self, t):
        r = self.poll.poll(t * 1000)
        if r is None:
            connects = len(self.single_sockets)
            to_close = int(connects * 0.05) + 1   # close 5% of sockets
            self.max_connects = connects - to_close
            closelist = list(self.single_sockets.values())
            random.shuffle(closelist)
            closelist = closelist[:to_close]
            for sock in closelist:
                self._close_socket(sock)
            return []
        return r

    def get_stats(self):
        return {'interfaces': self.interfaces,
                'port': self.port,
                'upnp': self.port_forwarded is not None}

    def shutdown(self):
        for ss in list(self.single_sockets.values()):
            try:
                ss.close()
            except (AssertionError, KeyError, ValueError, OSError):
                pass
        for server in self.servers.values():
            try:
                server.close()
            except OSError:
                pass
        if self.port_forwarded is not None:
            UPnP_close_port(self.port_forwarded)
