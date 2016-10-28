from __future__ import unicode_literals

import unittest
import json

from io import BytesIO, StringIO

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from pico import PicoApp


class TestJSONArgs(unittest.TestCase):

    def setUp(self):
        kwargs = {
            'str_arg': 'hello world',
            'int_arg': 42,
            'float_arg': 3.14,
            'list_arg': [1, 2, 3],
        }
        builder = EnvironBuilder(
            method='POST',
            data=json.dumps(kwargs),
            query_string={'int_arg2': 42}
        )
        builder.content_type = 'application/json'
        self.request = Request(builder.get_environ())
        self.app = PicoApp()

    def test_str_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['str_arg'], 'hello world')

    def test_int_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['int_arg'], 42)

    def test_querystring_int_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['int_arg2'], 42)

    def test_list_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['list_arg'], [1, 2, 3])


class TestPOSTArgs(unittest.TestCase):

    def setUp(self):
        kwargs = {
            'str_arg': 'hello world',
            'int_arg': 42,
            'float_arg': 3.14,
            'list_arg': [1, 2, 3],
            'upload': (BytesIO(b'some file contents'), 'test.txt'),
        }
        builder = EnvironBuilder(
            method='POST',
            data=kwargs,
            query_string={'int_arg2': 42}
        )
        self.request = Request(builder.get_environ())
        self.app = PicoApp()

    def test_str_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['str_arg'], 'hello world')

    def test_int_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['int_arg'], 42)

    def test_querystring_int_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['int_arg2'], 42)

    def test_file_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['upload'].read(), b'some file contents')

    def test_list_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['list_arg'], [1, 2, 3])


class TestGETArgs(unittest.TestCase):

    def setUp(self):
        kwargs = {
            'str_arg': 'hello world',
            'int_arg': 42,
            'float_arg': 3.14,
            'list_arg': [1, 2, 3],
        }
        builder = EnvironBuilder(
            method='GET',
            query_string=kwargs
        )
        self.request = Request(builder.get_environ())
        self.app = PicoApp()

    def test_str_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['str_arg'], 'hello world')

    def test_int_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['int_arg'], 42)

    def test_list_arg(self):
        args = self.app.parse_args(self.request)
        self.assertEqual(args['list_arg'], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
