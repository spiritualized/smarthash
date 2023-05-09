import qbittorrentapi
from qbittorrentapi import APIError

from OutputPlugins.base_output import OutputPlugin
from functions import PluginError
from pluginmixin import PluginOutput


class QBittorrent(OutputPlugin):
    title = "qBittorrent"

    def validate_config(self):
        """
        Validate plugin-specific configuration, raise
        :raises PluginError on invalid configuration parameter
        """
        for value in ['host', 'username', 'password', 'add paused']:
            if value not in self.config or not self.config[value]:
                raise PluginError(f"Invalid qBittorrent configuration value for '{value}'")
        self.__get_port()
        self.__get_add_paused()

    def test_connection(self) -> None:
        """
        Ensure that a connection to the external program can be made
        :raises PluginError if a connection cannot be established
        """
        qbt_client = qbittorrentapi.Client(host='localhost',
                                           port=int(self.config['port']),
                                           username=self.config['username'],
                                           password=self.config['password'])

        try:
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            raise PluginError("Failed to connect to qBittorrent: login failed")
        except (qbittorrentapi.APIConnectionError, qbittorrentapi.APIError) as e:
            raise PluginError("Failed to connect to qBittorrent") from e
        qbt_client.auth_log_out()

    def handle(self, plugin_output: PluginOutput, path: str):
        """
        Send torrent file to an external program
        :param plugin_output: structure containing the finalized torrent
        :param path: the path being hashed
        :raises PluginError if the torrent cannot be processed
        """
        with qbittorrentapi.Client(host='localhost',
                                   port=self.__get_port(),
                                   username=self.config['username'],
                                   password=self.config['password']) as client:
            result = client.torrents_add(torrent_files=plugin_output.torrent_data,
                                         save_path=path,
                                         is_paused=self.__get_add_paused(),
                                         use_auto_torrent_management=False)
            if result != 'Ok.':
                raise PluginError('client rejected the torrent')

        return

    def __get_port(self) -> int:
        if 'port' not in self.config or not self.config['port'].isnumeric():
            raise PluginError(f"Invalid {self.title} configuration value for 'port'")
        port = int(self.config['port'])
        if port < 0 or port > 65535:
            raise PluginError(f"deluge port out of range ({port})")
        return port

    def __get_add_paused(self) -> bool:
        if 'add paused' not in self.config:
            return True
        if self.config['add paused'].lower() not in ['true', 'false']:
            raise PluginError(f"Invalid {self.title} configuration for value 'add paused': "
                              f"must be one of [true, false]")
        if self.config['add paused'].lower() == 'true':
            return True
        elif self.config['add paused'].lower() == 'false':
            return False
