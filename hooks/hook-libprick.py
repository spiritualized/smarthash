# #!/usr/bin/env python3
# # coding=utf-8

from PyInstaller.compat import is_linux, is_win

if is_win:
    path = 'venv-win/Lib/site-packages/av'
    datas = [
        ('{0}/avcodec-58.dll'.format(path), '.'),
        ('{0}/avformat-58.dll'.format(path), '.'),
        ('{0}/avutil-56.dll'.format(path), '.'),
        ('{0}/swresample-3.dll'.format(path), '.'),
    ]
elif is_linux:
    hiddenimports = ['av']
