from typing import List

from functions import BulkMode
from pluginmixin import PluginMixin, PluginOutput


class BasePlugin(PluginMixin):

    def get_bulk_mode(self, args) -> BulkMode:
        """
        Implement to specify which bulk mode scanner should be used, based on parameters sent to the plugin
        BulkMode.STANDARD: each subfolder in the scan path is treated as an item
        BulkMode.MUSIC: each music release, identified by the recursive scanner, is treated as an item
        :param args:
        :return:
        """
        return BulkMode.STANDARD

    def get_blacklist_file_extensions(self, args) -> List[str]:
        """
        Implement this function to disallow file types based on parameters to the plugin
        Use to e.g. blacklist archives for media torrents
        :param args: plugin parameters
        :return: List of disallowed file extensions
        """
        return []

    def validate_settings(self) -> None:
        """
        # TODO remove
        """
        pass

    def get_update(self, smarthash_version) -> str:
        """
        # TODO remove
        Retrieves an updated version of the current plugin
        :param smarthash_version: Version of smarthash core
        :return: text containing an updated plugin's code
        """
        return ""

    def validate_parameters(self, args) -> None:
        """
        Implement this function to validate parameters passed to the plugin
        :raises: PluginError if an invalid combination of parameters are passed
        """
        pass

    def early_validation(self, path, data) -> None:
        """
        Implement this function to do server-size content validation before uploading
        Use to avoid unnecessarily hashing content which would not be accepted
        :param path: Path to the torrent's contents
        :param data: plugin parameters and content metadata
        """
        pass

    def handle(self, data) -> PluginOutput:
        """
        Required. This function contains the upload logic for the plugin
        :param data: plugin parameters and content metadata
        :return: object containing the finalized .torrent file
        """
        pass
