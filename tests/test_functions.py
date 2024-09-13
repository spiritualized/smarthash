import json
import os
import unittest

import requests
from mockito import when, ANY, verify

from functions import error, requests_retriable_post, requests_retriable_put, requests_retriable_get, \
    list_files, get_mime_type, MagicError, mp3_info, imdb_id_to_url, imdb_url_to_id, \
    ValidationError, verify_imdb, extract_metadata, filter_screenshot_paths
from tests.test_smarthash import FIXTURES_ROOT, PATHS


class FunctionTests(unittest.TestCase):

    def test_error(self):
        with self.assertRaises(SystemExit):
            error('Not valid json')
        with self.assertRaises(SystemExit):
            error('["Single error"]')
        with self.assertRaises(SystemExit):
            error('["First error", "Second error"]')

    def test_requests_retriable_post(self):
        when(requests).post(ANY).thenReturn(None)
        requests_retriable_post('http://test')
        verify(requests, times=1).post(ANY)

    def test_requests_retriable_put(self):
        when(requests).put(ANY).thenReturn(None)
        requests_retriable_put('http://test')
        verify(requests, times=1).put(ANY)

    def requests_retriable_get(self):
        when(requests).get(ANY).thenReturn(None)
        requests_retriable_get('http://test')
        verify(requests, times=1).get(ANY)

    def test_list_files(self):
        list_path = os.path.join(FIXTURES_ROOT, 'audio')
        expected = [
            os.path.join("audio", "Example Artist - 2000 - Example Album 1 [CBR128]", "Example Track.mp3"),
            os.path.join("audio", "Pink Floyd - 1973 - The Dark Side of the Moon [CBR128]", "Example Track.mp3")
        ]
        file_list = list_files(list_path)

        assert file_list == expected

    def test_get_mime_type(self):
        assert get_mime_type(PATHS['video_file']) == 'video/mp4'
        assert get_mime_type(PATHS['audio_1_file']) == 'audio/mpeg'

        with self.assertRaises(MagicError):
            get_mime_type('nonexistent_path')

    def test_mp3_info(self):
        mp3_info_output = mp3_info(PATHS['audio_1_file'])
        assert mp3_info_output == {'xing_header': 'INFO', 'method': 'CBR'}

    def test_imdb_id_to_url(self):
        assert imdb_id_to_url('1234567') == 'https://www.imdb.com/title/tt1234567/'

    def test_imdb_url_to_id(self):
        assert imdb_url_to_id('https://www.imdb.com/title/tt1234567') == '1234567'
        assert imdb_url_to_id('https://www.imdb.com/title/tt1234567/') == '1234567'
        assert imdb_url_to_id('https://www.imdb.com/title/tt12345678') == '12345678'

        with self.assertRaises(ValidationError):
            imdb_url_to_id('https://www.imdb.com/title/tt123456')

    def test_verify_imdb(self):
        with self.assertRaises(ValidationError):
            verify_imdb('0000000')

        verify_imdb('1234567')

    def test_extract_metadata(self):
        with open(os.path.join(FIXTURES_ROOT, 'metadata', 'example-mp4-file-small.json')) as f:
            expected = f.read()

            metadata = extract_metadata(PATHS['video'])
            assert expected == json.dumps(metadata)

    def test_filter_screenshot_paths(self):
        test_paths = [
            "C:\\root\\folder1\\video01.avi",
            "C:\\root\\folder1\\video02.avi",
            "C:\\root\\folder1\\video03.avi",
            "C:\\root\\folder1\\video04.avi",
            "C:\\root\\folder1\\video05.avi",
            "C:\\root\\folder1\\video06.avi",
            "C:\\root\\folder2\\video07.avi",
            "C:\\root\\folder2\\video08.avi",
        ]

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")

        # <= 8, no filtering
        assert len(test_paths) == len(filtered_paths)

        test_paths.append("C:\\root\\folder2\\video09.avi")

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")
        expected = [
            "C:\\root\\folder1\\video01.avi",
            "C:\\root\\folder2\\video07.avi",
        ]
        # Multiple top-level folders, 2 expected
        assert filtered_paths == test_paths[:8]

        test_paths = [
            "C:\\root\\folder1\\subfolder01\\video01.avi",
            "C:\\root\\folder1\\subfolder02\\video02.avi",
            "C:\\root\\folder1\\subfolder03\\video03.avi",
            "C:\\root\\folder2\\subfolder04\\video04.avi",
            "C:\\root\\folder2\\subfolder05\\video05.avi",
            "C:\\root\\folder2\\subfolder06\\video06.avi",
            "C:\\root\\folder3\\subfolder07\\video07.avi",
            "C:\\root\\folder3\\subfolder08\\video08.avi",
            "C:\\root\\folder3\\subfolder09\\video09.avi",
        ]

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")

        # First 8 paths expected
        expected = [
            "C:\\root\\folder1\\subfolder01\\video01.avi",
            "C:\\root\\folder2\\subfolder04\\video04.avi",
            "C:\\root\\folder3\\subfolder07\\video07.avi",
        ]
        assert filtered_paths == expected

        test_paths = [
            "C:\\root\\folder1\\subfolder01\\video01.avi",
            "C:\\root\\folder1\\subfolder02\\video02.avi",
            "C:\\root\\folder1\\subfolder03\\video03.avi",
            "C:\\root\\folder1\\subfolder04\\video04.avi",
            "C:\\root\\folder1\\subfolder05\\video05.avi",
            "C:\\root\\folder1\\subfolder06\\video06.avi",
            "C:\\root\\folder2\\subfolder07\\video07.avi",
            "C:\\root\\folder2\\subfolder08\\video08.avi",
            "C:\\root\\folder2\\subfolder09\\video09.avi",
            "C:\\root\\folder2\\subfolder10\\video10.avi",
            "C:\\root\\folder2\\subfolder11\\video11.avi",
            "C:\\root\\folder2\\subfolder12\\video12.avi",
        ]

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")

        # First 8 paths expected
        assert filtered_paths == test_paths[:8]

        test_paths = [
            "C:\\root\\folder01\\subfolder01\\video01.avi",
            "C:\\root\\folder02\\subfolder02\\video02.avi",
            "C:\\root\\folder03\\subfolder03\\video03.avi",
            "C:\\root\\folder04\\subfolder04\\video04.avi",
            "C:\\root\\folder05\\subfolder05\\video05.avi",
            "C:\\root\\folder06\\subfolder06\\video06.avi",
            "C:\\root\\folder07\\subfolder07\\video07.avi",
            "C:\\root\\folder08\\subfolder08\\video08.avi",
            "C:\\root\\folder09\\subfolder09\\video09.avi",
            "C:\\root\\folder10\\subfolder10\\video10.avi",
            "C:\\root\\folder11\\subfolder11\\video11.avi",
            "C:\\root\\folder12\\subfolder12\\video12.avi",
        ]

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")

        # First 8 paths expected
        assert filtered_paths == test_paths[:8]

        test_paths = [
            "C:\\root\\folder0\\video01.avi",
            "C:\\root\\folder0\\video02.avi",
            "C:\\root\\folder0\\video03.avi",
            "C:\\root\\folder0\\video04.avi",
            "C:\\root\\folder0\\video05.avi",
            "C:\\root\\folder0\\video06.avi",
            "C:\\root\\folder0\\video07.avi",
            "C:\\root\\folder0\\video08.avi",
            "C:\\root\\folder0\\video09.avi",
            "C:\\root\\folder0\\video10.avi",
            "C:\\root\\folder0\\video11.avi",
            "C:\\root\\folder0\\video12.avi",
        ]

        filtered_paths = filter_screenshot_paths(test_paths, "C:\\root")

        # First 8 paths expected
        assert filtered_paths == test_paths[:8]