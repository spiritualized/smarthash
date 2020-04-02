#!/usr/bin/env python3
# coding=utf-8

from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import PY_DYLIB_PATTERNS

PY_DYLIB_PATTERNS.extend(['lib*.so.[0-9]*'])

binaries = collect_dynamic_libs('pymediainfo')
