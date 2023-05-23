import re

import requests
from requests.auth import HTTPBasicAuth

from OutputPlugins.base_output import OutputPlugin
from functions import PluginError
from pluginmixin import PluginOutput


class UtorrentSession:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.base_url = f"http://{host}:{port}/gui"
        self.auth = HTTPBasicAuth(username, password)
        self.token = None
        self.session = requests.Session()

        self.get('/')  # sanity check
        http_resp = self.get('/token.html')
        self.token = re.findall(r"[\w=_-]{60,64}", http_resp.text)[0]

    def get(self, location: str, **kwargs) -> requests.Response:
        """Wrap requests Session.get, inject HTTP basic auth"""
        return self._make_request(self.session.get, location, **kwargs)

    def post(self, location: str, **kwargs) -> requests.Response:
        """Wrap requests Session.post, inject uTorrent token"""
        return self._make_request(self.session.post, location, **kwargs)

    def _make_request(self, session_func, location: str, **kwargs) -> requests.Response:
        """Call requests Session.get, Session.post and handle errors"""
        kwargs_new = kwargs
        kwargs_new['auth'] = self.auth  # inject HTTP basic auth token

        if self.token:
            if 'params' not in kwargs_new:
                kwargs_new['params'] = {}
            if type(kwargs_new['params']) == dict:
                kwargs_new['params']['token'] = self.token  # inject uTorrent token
            elif type(kwargs_new['params']) == list:  # handle params type of list
                kwargs_new['params'].insert(0, ('token', self.token))

        try:
            http_resp = session_func(f"{self.base_url}{location}", **kwargs_new)
        except requests.exceptions.ConnectionError as e:
            raise PluginError("Connection timed out. Check the host/port configuration") from e

        if http_resp.status_code == 401:
            raise PluginError(f"login failed, verify your username/password")
        elif http_resp.status_code == 400 and http_resp.text.strip() == "invalid request":
            raise PluginError("webUI is not enabled, OR INVALID REQUEST")
        elif "WebUI does not seem to be installed" in http_resp.text:
            raise PluginError("webUI is not installed")

        if http_resp.headers['content-type'] == 'text/plain':
            if http_resp.json().get('error'):
                raise PluginError(http_resp.json()['error'])

        return http_resp


class UTorrent(OutputPlugin):
    title = "uTorrent"

    def __init__(self, config=None):
        self.session = None
        super().__init__(config)

    def validate_config(self):
        """
        Validate plugin-specific configuration, raise
        :raises PluginError on invalid configuration parameter
        """
        for value in ['host', 'username', 'password']:
            if value not in self.config or not self.config[value]:
                raise PluginError(f"Invalid {self.title} configuration value for '{value}'")
        self._get_port()
        self._get_add_paused()

    def test_connection(self) -> None:
        """
        Ensure that a connection to the external program can be made
        :raises PluginError if a connection cannot be established
        """
        self._get_session()

    def handle(self, plugin_output: PluginOutput, path: str):
        """
        Send torrent file to an external program
        :param plugin_output: structure containing the finalized torrent
        :param path: the path being hashed
        :raises PluginError if the torrent cannot be processed
        """
        utorrent = self._get_session()

        # Get existing settings
        http_resp = self.session.get('/', params={'action': 'getsettings'})
        existing_settings = {x[0]: x[2] for x in http_resp.json()['settings']
                             if x[0] in ['dir_active_download_flag', 'dir_active_download', 'torrents_start_stopped']}

        # remap strings
        remaps = {'false': 0, 'true': 1}
        for key in existing_settings.keys():
            if existing_settings[key] in remaps.keys():
                existing_settings[key] = remaps[existing_settings[key]]

        # Set the download directory
        utorrent.get('/', params=[
            ('action', 'setsetting'),
            ('s', 'dir_active_download_flag'),
            ('v', '1'),
            ('s', 'dir_active_download'),
            ('v', path),
            ('s', 'dir_completed_download_flag'),
            ('v', '0'),
            ('s', 'torrents_start_stopped'),
            ('v', int(self._get_add_paused()))
        ])

        try:
            # Upload the torrent
            utorrent.post('/', params={'action': 'add-file'}, files={'torrent_file': plugin_output.torrent_data})

        finally:
            # Restore original settings
            utorrent.get('/', params=[
                ('action', 'setsetting'),
                ('s', 'dir_active_download_flag'),
                ('v', int(existing_settings['dir_active_download_flag'])),
                ('s', 'dir_active_download'),
                ('v', existing_settings['dir_active_download']),
                ('s', 'torrents_start_stopped'),
                ('v', int(existing_settings['torrents_start_stopped']))
            ])

    def _get_session(self) -> UtorrentSession:
        """Returns a UTorrentSession singleton"""
        if not self.session:
            self.session = UtorrentSession(self.config['host'], self.config['port'], self.config['username'],
                                           self.config['password'])
        return self.session
