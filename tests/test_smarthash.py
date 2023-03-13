import os
import sys
import unittest

from mockito import when, verify, ANY, unstub

import baseplugin
from Plugins.default import SmarthashPlugin as DefaultPlugin
from functions import BulkMode
from smarthash import SmartHash

FIXTURES_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'fixtures'))

PATHS = {
    'audio_1': os.path.join(FIXTURES_ROOT, 'audio', 'Example Artist - 2000 - Example Album 1 [CBR128]'),
    'audio_1_file': os.path.join(FIXTURES_ROOT, 'audio', 'Example Artist - 2000 - Example Album 1 [CBR128]',
                                 '01 - Example Title.mp3'),
    'audio_2': os.path.join(FIXTURES_ROOT, 'audio', 'Example Artist - Example Album 2'),
    'audio_bulk': os.path.join(FIXTURES_ROOT, 'audio'),
    'video': os.path.join(FIXTURES_ROOT, 'video', 'video_1'),
    'video_file': os.path.join(FIXTURES_ROOT, 'video', 'video_1', 'example-mp4-file-small.mp4'),
    'video_bulk': os.path.join(FIXTURES_ROOT, 'video'),
}


class SmartHashTests(unittest.TestCase):

    def setUp(self) -> None:
        del sys.argv[1:]

    def tearDown(self) -> None:
        unstub()

    def test_init(self):
        sys.argv.extend([PATHS['video']])

        smarthash = SmartHash()

        assert smarthash.args.plugin == 'default'
        assert smarthash.args.path == PATHS['video']

    def test_process_invalid_dir(self):
        params = [
            os.path.join(FIXTURES_ROOT, 'nonexistent_path'),
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()
        with self.assertRaises(SystemExit):
            smarthash.process()

    def test_process_standard(self):
        params = [
            PATHS['video'],
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()

        when(smarthash).process_folder_wrapper(ANY).thenReturn(None)
        smarthash.process()
        verify(smarthash, times=1).process_folder_wrapper(params[0])

    def test_process_bulk(self):
        params = [
            '--bulk',
            PATHS['video_bulk'],
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()

        when(smarthash).process_folder_wrapper(ANY).thenReturn(None)

        smarthash.process()

        verify(smarthash, times=1).process_folder_wrapper(PATHS['video'])
        verify(smarthash, times=1).process_folder_wrapper(ANY)

    def test_process_bulk_music(self):
        params = [
            '--bulk',
            PATHS['audio_bulk'],
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()

        when(smarthash).process_folder_wrapper(ANY).thenReturn(None)
        when(baseplugin.BasePlugin).get_bulk_mode(ANY).thenReturn(BulkMode.MUSIC)

        smarthash.process()
        verify(smarthash, times=1).process_folder_wrapper(PATHS['audio_1'])
        verify(smarthash, times=1).process_folder_wrapper(PATHS['audio_2'])
        verify(smarthash, times=2).process_folder_wrapper(ANY)

    def test_process_folder(self):
        params = [
            '--plugin',
            'default',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()
        plugin = DefaultPlugin()
        smarthash.plugins['default'] = plugin

        when(plugin).handle(ANY).thenReturn(None)

        smarthash.process_folder(PATHS['video'], plugin)

        verify(plugin, times=1).handle(ANY)

    def test_extract_images(self):
        params = [
            PATHS['video']
        ]
        sys.argv.extend(params)

        smarthash = SmartHash()
        images = smarthash.extract_images([PATHS['video_file']])
        assert len(images) == 1
