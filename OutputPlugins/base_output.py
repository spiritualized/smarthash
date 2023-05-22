from functions import PluginError
from pluginmixin import PluginOutput


class OutputPlugin:
    title = "No-op"

    def __init__(self, config=None):
        self.config = config
        self.validate_config()
        self.test_connection()

    def validate_config(self):
        """
        Validate plugin-specific configuration, raise
        :raises PluginError on invalid configuration parameter
        """
        pass

    def test_connection(self) -> None:
        """
        Ensure that a connection to the external program can be made
        :raises PluginError if a connection cannot be established
        """
        return

    def handle(self, plugin_output: PluginOutput, path: str):
        """
        Send torrent file to an external program
        :param plugin_output: structure containing the finalized torrent
        :param path: the path being hashed
        :raises PluginError if the torrent cannot be processed
        """
        return

    def _get_port(self) -> int:
        if 'port' not in self.config or not self.config['port'].isnumeric():
            raise PluginError(f"Invalid {self.title} configuration value for 'port'")
        port = int(self.config['port'])
        if port < 0 or port > 65535:
            raise PluginError(f"deluge port out of range ({port})")
        return port

    def _get_add_paused(self) -> bool:
        if 'add paused' not in self.config:
            return True
        if self.config['add paused'].lower() not in ['true', 'false']:
            raise PluginError(f"Invalid {self.title} configuration for value 'add paused': "
                              f"must be one of [true, false]")
        if self.config['add paused'].lower() == 'true':
            return True
        elif self.config['add paused'].lower() == 'false':
            return False
