# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

hidden_imports = [
			 'rasterio._shim', 
			 'numpy.random.common', 
			 'numpy.random.bounded_integers', 
			 'numpy.random.entropy', 
			 'rasterio.control',
			 'rasterio.sample', 
			 'rasterio.vrt', 
			 'rasterio._features']

env_path = Path(os.environ['CONDA_PREFIX'])
bins = env_path / 'Library' / 'bin'


binaries = [
    (str(bins / 'geos.dll'), '.'),
    (str(bins / 'geos_c.dll'), '.'),
    (str(bins / 'pdal.exe'), '.')
]

proj_path = env_path / 'Library' / 'share' / 'proj'
proj_datas = [
    (str(proj_path / 'CH'), 'pyproj'),
    (str(proj_path / 'GL27'), 'pyproj'),
    (str(proj_path / 'ITRF2000'), 'pyproj'),
    (str(proj_path / 'ITRF2008'), 'pyproj'),
    (str(proj_path / 'ITRF2014'), 'pyproj'),
    (str(proj_path / 'nad.lst'), 'pyproj'),
    (str(proj_path / 'nad27'), 'pyproj'),
    (str(proj_path / 'nad83'), 'pyproj'),
    (str(proj_path / 'other.extra'), 'pyproj'),
    (str(proj_path / 'proj.db'), 'pyproj'),
    (str(proj_path / 'proj.ini'), 'pyproj'),
    (str(proj_path / 'world'), 'pyproj')
]

datas = collect_data_files('pyproj') \
		+ proj_datas

a = Analysis(['quicklook.py'],
             pathex=['C:\\Users\\Nick.Forfinski-Sarko\\source\\repos\\QuickLookDEM'],
             binaries=binaries,
             datas=datas,
             hiddenimports=hidden_imports,
             hookspath=[],
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
          name='QuickLook',
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
               name='QuickLook')
