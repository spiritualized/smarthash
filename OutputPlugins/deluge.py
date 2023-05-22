import random
from typing import Dict

import requests

from OutputPlugins.base_output import OutputPlugin
from functions import PluginError
from pluginmixin import PluginOutput


class DelugeSession:
    def __init__(self, host: str, port: int, password: str):
        self.base_url = f"http://{host}:{port}"
        self.password = password
        self.session = requests.Session()

        req = {
            "method": "auth.login",
            "params": [self.password],
            "id": random.randint(1, 1000000)
        }

        resp = self.post('/json', json=req)

        if not resp['result']:
            raise PluginError("Login failed")

    def post(self, location: str, **kwargs) -> Dict:
        # TODO cookies should be persisted in the requests session
        kwargs['cookies'] = requests.utils.dict_from_cookiejar(self.session.cookies)
        try:
            http_resp = self.session.post(f"{self.base_url}/{location}", **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise PluginError("Failed to connect to deluge: ConnectionError") from e

        if http_resp.status_code != 200:
            PluginError(f"Failed to connect to deluge: HTTP response f{http_resp.status_code}")

        resp = http_resp.json()

        if resp.get('error'):
            raise PluginError(resp['error']['message'])

        return resp


class Deluge(OutputPlugin):
    title = "deluge"

    def __init__(self, config=None):
        self.session = None
        super().__init__(config)

    def validate_config(self):
        """
        Validate plugin-specific configuration, raise
        :raises PluginError on invalid configuration parameter
        """
        for value in ['host', 'password']:
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
        deluge = self._get_session()

        # Check the torrent hash isn't already in deluge
        req = {
            "method": "web.update_ui",
            "params": [["download_location"], {}],
            "id": random.randint(1, 1000000)
        }

        resp = deluge.post('/json', json=req)

        if plugin_output.get_hex_hash() in resp['result']['torrents']:
            raise PluginError("Torrent hash already exists")

        # Upload the torrent
        resp = deluge.post("/upload", files={'file': plugin_output.torrent_data})

        if not resp['success']:
            raise PluginError("Torrent upload failed")

        # Add the uploaded torrent
        req = {
            "method": "web.add_torrents",
            "params": [
                [
                    {
                        "path": resp['files'][0],
                        "options": {
                            "file_priorities": [
                                1,
                                1
                            ],
                            "add_paused": self._get_add_paused(),
                            "sequential_download": False,
                            "pre_allocate_storage": False,
                            "download_location": path,
                            "move_completed": False,
                            "move_completed_path": path,
                            "max_connections": -1,
                            "max_download_speed": -1,
                            "max_upload_slots": -1,
                            "max_upload_speed": -1,
                            "prioritize_first_last_pieces": False,
                            "seed_mode": False,
                            "super_seeding": False
                        }
                    }
                ]
            ],
            "id": random.randint(1, 1000000)
        }

        resp = deluge.post('/json', json=req)

        if not resp['result'][0]:
            raise PluginError("Failed to add torrent")

    def _get_session(self) -> DelugeSession:
        """Returns a DelugeSession singleton"""
        if not self.session:
            self.session = DelugeSession(self.config['host'], self.config['port'], self.config['password'])
        return self.session
