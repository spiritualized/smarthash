import os
import sys
import unittest

from mockito import unstub, when, ANY

from smarthash import SmartHash
from tests.MockFile import MockFile
from tests.test_smarthash import FIXTURES_ROOT, PATHS


class SavePluginTests(unittest.TestCase):

    def setUp(self) -> None:
        del sys.argv[1:]

    def tearDown(self) -> None:
        MockFile.reset()
        unstub()

    def test_handle(self):
        params = [
            '--plugin',
            'save',
            PATHS['video'],
        ]
        sys.argv.extend(params)

        fixture_root = os.path.join(FIXTURES_ROOT, 'metadata')
        fixture_filenames = [
            'mediainfo.txt',
            'screenshot_0.jpeg',
            'screenshot_1.jpeg',
            'screenshot_2.jpeg',
            'screenshot_3.jpeg',
            'video_1.torrent'
        ]
        fixture_data = []
        for filename in fixture_filenames:
            with open(os.path.join(fixture_root, filename), 'rb') as file_1:
                fixture_data.append(file_1.read())

        when(os).makedirs(ANY).thenReturn(None)

        intercept_root = os.path.join(FIXTURES_ROOT, 'video', 'video_1_smarthash')
        with MockFile([os.path.join(intercept_root, x) for x in fixture_filenames]):
            smarthash = SmartHash()
            smarthash.process()

            for i in range(1, len(fixture_filenames)):  # Skip the mediainfo
                assert len(fixture_data[i]) == \
                       len(MockFile.get_data(os.path.join(intercept_root, fixture_filenames[i])))

            for i in range(1, len(fixture_filenames)-1):
                assert fixture_data[i] == MockFile.get_data(os.path.join(intercept_root, fixture_filenames[i]))

            # skip the 'created' field on the .torrent
            assert fixture_data[-1][70:] == MockFile.get_data(os.path.join(intercept_root, fixture_filenames[-1]))[70:]
