import transmission_rpc
from transmission_rpc.error import TransmissionAuthError, TransmissionConnectError, TransmissionTimeoutError, \
    TransmissionError

from OutputPlugins.base_output import OutputPlugin
from functions import PluginError
from pluginmixin import PluginOutput


class Transmission(OutputPlugin):
    title = "Transmission"

    def __init__(self, config=None):
        self.client = None
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
        self._get_client()

    def handle(self, plugin_output: PluginOutput, path: str):
        """
        Send torrent file to an external program
        :param plugin_output: structure containing the finalized torrent
        :param path: the path being hashed
        :raises PluginError if the torrent cannot be processed
        """
        client = self._get_client()

        try:
            client.add_torrent(torrent=plugin_output.torrent_data, download_dir=path, paused=self._get_add_paused())
        except TransmissionError as e:
            raise PluginError(e.message)

    def _get_client(self) -> transmission_rpc.Client:
        """Returns a transmission_rpc client singleton"""
        if not self.client:
            try:
                self.client = transmission_rpc.Client(host=self.config['host'],
                                                      port=self._get_port(),
                                                      username=self.config['username'],
                                                      password='abcd')
            except TransmissionAuthError as e:
                raise PluginError("Authentication error") from e
            except (TransmissionConnectError, TransmissionTimeoutError) as e:
                raise PluginError("Could not connect") from e
            except TransmissionError as e:
                raise PluginError(e.message)

        return self.client
