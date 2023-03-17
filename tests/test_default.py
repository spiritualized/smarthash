import builtins
import os
import sys
import unittest

from mockito import unstub, mock

from BitTornado.Meta.bencode import bdecode
from Plugins.default import SmarthashPlugin as DefaultPlugin
from functions import PluginError
from smarthash import SmartHash
from tests.MockFile import MockFile
from tests.test_smarthash import FIXTURES_ROOT, PATHS


class DefaultPluginTests(unittest.TestCase):

    def setUp(self) -> None:
        del sys.argv[1:]

    def tearDown(self) -> None:
        MockFile.reset()
        unstub()

    def test_early_validation(self):
        args = mock()
        args.destination = 'test'
        data = {
            'title': 'Test title',
            'args': args
        }

        default_plugin = DefaultPlugin()
        default_plugin.early_validation(FIXTURES_ROOT, data)

        args.destination = os.path.join('nonexistent path', 'test')
        with self.assertRaises(PluginError):
            default_plugin.early_validation(FIXTURES_ROOT, data)

    def test_handle(self):
        params = [
            '--plugin',
            'default',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        fixture_path = os.path.join(FIXTURES_ROOT, 'metadata', 'video_1.torrent')
        with open(fixture_path, 'rb') as file_1:
            expected = file_1.read()

        intercept_path = os.path.join(FIXTURES_ROOT, 'video', 'video_1.torrent')
        
        with MockFile(intercept_path):
            smarthash = SmartHash()
            smarthash.process()
    
            assert len(expected) == len(MockFile.get_data(intercept_path))
            assert expected[70:] == MockFile.get_data(intercept_path)[70:]  # skip the 'created' field

    def test_blacklist(self):
        params = [
            '--plugin',
            'default',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        intercept_path = os.path.join(FIXTURES_ROOT, 'video', 'video_1.torrent')

        with MockFile(intercept_path):
            smarthash = SmartHash()
            smarthash.process()

            torrent_metadata = bdecode(MockFile.get_data(intercept_path))
            torrent_paths = [x['path'] for x in torrent_metadata['info']['files']]

            assert ['Sample', 'Unwanted sample file.mp3'] not in torrent_paths
            assert torrent_paths == [['example-mp4-file-small.mp4'], ['video.nfo']]

    def test_disable_blacklist(self):
        params = [
            '--plugin',
            'default',
            '--disable-blacklist',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        intercept_path = os.path.join(FIXTURES_ROOT, 'video', 'video_1.torrent')

        with MockFile(intercept_path):
            smarthash = SmartHash()
            smarthash.process()

            torrent_metadata = bdecode(MockFile.get_data(intercept_path))
            torrent_paths = [x['path'] for x in torrent_metadata['info']['files']]

            assert ['Sample', 'Unwanted sample file.mp3'] in torrent_paths

    def test_file_extension_blacklist(self):
        params = [
            '--plugin',
            'default',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        intercept_path = os.path.join(FIXTURES_ROOT, 'video', 'video_1.torrent')

        with MockFile(intercept_path):
            smarthash = SmartHash()
            smarthash.process()

            torrent_metadata = bdecode(MockFile.get_data(intercept_path))
            torrent_paths = [x['path'] for x in torrent_metadata['info']['files']]

            assert ['unwanted.sfv'] not in torrent_paths
            assert torrent_paths == [['example-mp4-file-small.mp4'], ['video.nfo']]
