# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['quicklook.py'],
             pathex=['C:\\Users\\Nick.Forfinski-Sarko\\source\\repos\\QuickLookDEM'],
             binaries=[],
             datas=[],
             hiddenimports=[
			 'rasterio._shim', 
			 'numpy.random.common', 
			 'numpy.random.bounded_integers', 
			 'numpy.random.entropy', 
			 'rasterio.control', 
			 'rasterio.crs', 
			 'rasterio.sample', 
			 'rasterio.vrt', 
			 'rasterio._features'],
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
