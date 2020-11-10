import sys

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    import os
    from pathlib import Path
    import pyproj
    # logging.info('running in a PyInstaller bundle')
    cwd = Path.cwd()
    os.environ["PATH"] += os.pathsep + str(cwd)
    gdal_data_path = cwd / 'Library' / 'share' / 'gdal'
    proj_data_path = cwd / 'Library' / 'share' / 'proj'

    os.environ["GDAL_DATA"] = str(gdal_data_path)
    os.environ["GDAL_DATA"] = str(proj_data_path)

    #pyproj.datadir.set_data_dir(str(cwd / "pyproj"))

import os
import subprocess
import json
import numpy as np
from datetime import datetime
import multiprocessing as mp
from functools import partial
from pathlib import Path
import rasterio
import rasterio.merge
from rasterio.io import MemoryFile
from rasterio.crs import CRS
import PySimpleGUI as sg
from PySimpleGUI import OneLineProgressMeter as progress


os.environ["PYTHONUNBUFFERED"] = "1"

"""Multiprocessing variables"""
PROC_CNT = mp.cpu_count()
PROC_NAME = "{}_{}".format(mp.current_process().name, os.getpid())


class QuickLook:

    def __init__(self, val_to_grid):
        self.val_to_grid = val_to_grid
        self.profile = None

    @staticmethod
    def create_src(v):
        memfile = MemoryFile()
        src = memfile.open(**v[0])
        src.write(v[1])
        return src

    @staticmethod
    def get_las_info(las_path):

        def run_console_cmd(cmd):
            process = subprocess.Popen(cmd.split(' '), shell=False, 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.DEVNULL)
            output, error = process.communicate()
            returncode = process.poll()
            return returncode, output

        las = str(las_path).replace('\\', '/')
        cmd_str = 'pdal info {} --metadata'.format(las)
        metadata = run_console_cmd(cmd_str)[1].decode('utf-8')
        meta_dict = json.loads(metadata)
        srs = meta_dict['metadata']['srs']
        hor_wkt = srs['horizontal']

        major_version = meta_dict['metadata']['major_version']
        minor_version = meta_dict['metadata']['minor_version']
        las_version = f'{major_version}.{minor_version}'

        crs = None
        try:
            crs = CRS.from_string(hor_wkt)
            print(f'{las_path.name}: {crs.to_proj4()}')
        except Exception as e:
            print(f'{las_path.name} {e}')

        return crs, las_version

    def gen_mosaic(self, dem_dir, mosaic_path, vrts):
        if vrts:
            print('generating {}...'.format(mosaic_path))
            mosaic, out_trans = rasterio.merge.merge(vrts)
            self.profile = vrts[0].profile
            self.profile.update({
                'dtype': rasterio.uint32,
                'nodata': 0,
                'driver': "GTiff",
                'height': mosaic.shape[1],
                'width': mosaic.shape[2],
                'transform': out_trans})
            print(self.profile)
            mosaic = np.where(mosaic == -9999, 0, mosaic)
            print(mosaic)
            try:
                with rasterio.open(mosaic_path, 'w', **self.profile) as dest:
                    dest.write(mosaic.astype(rasterio.uint32))
            except Exception as e:
                print(e)
            finally:
                for vrt in vrts:
                    vrt.close()
        else:
            print('No DEM tiles were generated.')

    def create_surface(self, shared_dict, las_path):
        # TODO: Expose pipeline parameters in GUI
        import pdal
        from pathlib import Path

        crs, las_version = self.get_las_info(las_path)

        bathy_classes = {
            '1.2': 26,
            '1.4': 40
            }

        bathy_class = bathy_classes[las_version]
        las_str = str(las_path).replace('\\', '/')
        vrt_tiff = f"/vsimem/{las_path.stem}.tif"
        pdal_json = f"""{{
            "pipeline":[
                {{
                    "type": "readers.las",
                    "filename": "{las_str}"
                }},
                {{
                    "type": "filters.range",
                    "limits": "Classification[{bathy_class}:{bathy_class}]"
                }},
                {{
                    "filename": "{vrt_tiff}",
                    "gdaldriver": "GTiff",
                    "output_type": "{self.val_to_grid}",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                }}
            ]
        }}"""

        try:
            pipeline = pdal.Pipeline(pdal_json)
            __ = pipeline.execute()
            with rasterio.open(vrt_tiff, crs=crs) as src:
                data = src.read()
                profile = src.profile
            shared_dict[vrt_tiff] = [profile, data]
        except Exception as e:
            print(e)

    def create_surface_multiprocess(self, las_paths, num_las):
        shared_dict = mp.Manager().dict()
        p = mp.Pool(int(PROC_CNT / 2))

        # Initialize progress bar so that it shows from onset
        progress(f'Generating {self.val_to_grid} raster', 0, num_las, "pbar")
        func = partial(self.create_surface, shared_dict)
        for i, __ in enumerate(p.imap(func, las_paths)):
            time_stamp = datetime.now().isoformat()
            print("{}: {} / {}".format(time_stamp, i + 1, num_las))
            msg_str = f'Generating {self.val_to_grid} raster'
            progress(msg_str, i + 1, num_las, "pbar")

        return p, shared_dict


def create_quicklook(dir, val_to_grid):
    las_dir = Path(dir)
    las_paths = list(las_dir.glob('*.las'))
    num_las = len(list(las_paths))
    if num_las <= 0:
        print("No las files found")
        exit(1)

    ql = QuickLook(val_to_grid)
    p, p_dict = ql.create_surface_multiprocess(las_paths, num_las)
    p.close()
    p.join()

    vrts = [ql.create_src(v) for k, v in p_dict.items()]
    quick_look_path = las_dir / f'QUICK_LOOK_{val_to_grid}.tif'
    ql.gen_mosaic(las_dir, quick_look_path, vrts)
    print('DONE!')


def create_gui():
    vals_to_grid = ['mean', 'count']
    bathy_classs = [26, 40]

    layout = [
        [sg.Output(size=(100, 20))],
        [sg.Text('Las directory:', size=(12, 1)), 
         sg.In(key='las_dir'), 
         sg.FolderBrowse()],
        [sg.Text('Value to Grid'), 
         sg.Combo(vals_to_grid, key='val_to_grid')],
        [sg.Button('Create QLDEM')],
        [sg.Button('EXIT')]
        ]

    window = sg.Window('Quick Look (v1.0.0-rc3)', layout)

    return window

    
if __name__ == '__main__':
    # Required for pyinstaller support of multiprocessing
    mp.freeze_support()

    window = create_gui()
    while True:      
        (event, value) = window.Read() 
        print(json.dumps(value, indent=2))
        if event == 'EXIT'  or event is None:      
            break # exit button clicked    
        elif event == 'Create QLDEM':      
            print(value['las_dir'])
            if os.path.isdir(value['las_dir']):
                create_quicklook(value['las_dir'],
                                 value['val_to_grid'])
            else:
                print("'{}' is not a valid directory".format(value['las_dir']))
    window.Close()
