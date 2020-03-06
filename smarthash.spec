# -*- mode: python ; coding: utf-8 -*-
import platform

block_cipher = None

additional_binaries = []

if platform.system() == "Windows":
    additional_binaries = [('MediaInfo.dll', '.')]
elif platform.system() == "Linux":
    additional_binaries=[
        ('/usr/lib/x86_64-linux-gnu/libmediainfo.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libzen.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libmms.so.0', '.'),
        ('/usr/lib/x86_64-linux-gnu/libtinyxml2.so.2', '.')]

a = Analysis(['smarthash.py'],
             pathex=[],
             binaries=[],
             datas=[('Plugins', 'Plugins')],
             hiddenimports=[],
             hookspath=['hooks'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='smarthash',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='smarthash')
