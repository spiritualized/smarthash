import json
import os
import unittest

import requests
from mockito import when, ANY, verify

from functions import error, requests_retriable_post, requests_retriable_put, requests_retriable_get, img_key_variance, \
    list_files, get_mime_type, MagicError, mp3_info, imdb_id_to_url, imdb_url_to_id, ValidationError, verify_imdb, \
    extract_metadata, img_key_order
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

    def test_img_key_variance(self):
        assert img_key_variance(['first', 'second']) == 'second'

    def test_img_key_order(self):
        assert img_key_order(['first', 'second']) == 'first'

    def test_list_files(self):
        list_path = os.path.join(FIXTURES_ROOT, 'audio')
        expected = [
            """audio\\Example Artist - 2000 - Example Album 1 [CBR128]\\Example Track.mp3""",
            """audio\\Example Artist - 2000 - Example Album 2 [CBR128]\\Example Track.mp3"""
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
