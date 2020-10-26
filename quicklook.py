import os
import json
from datetime import datetime
import multiprocessing as mp
from functools import partial
from pathlib import Path
import rasterio
import rasterio.merge
from rasterio.io import MemoryFile
import PySimpleGUI as sg
from PySimpleGUI import OneLineProgressMeter as progress
#import pathos
#import pathos.pools as pp

os.environ["PYTHONUNBUFFERED"] = "1"

"""Multiprocessing variables"""
PROC_CNT = mp.cpu_count()
PROC_NAME = "{}_{}".format(mp.current_process().name, os.getpid())


class QuickLook:

    def __init__(self):
        self.profile = None

    @staticmethod
    def create_src(v):
        memfile = MemoryFile()
        src = memfile.open(**v[0])
        print(src.crs)
        src.write(v[1])
        return src

    def gen_mosaic(self, dem_dir, quick_look_path, vrts):
        if vrts:
            print('generating {}...'.format(quick_look_path))
            mosaic, out_trans = rasterio.merge.merge(vrts)
            self.profile = vrts[0].profile
            self.profile.update({
                'nodata': 0,
                'driver': "GTiff",
                'height': mosaic.shape[1],
                'width': mosaic.shape[2],
                'transform': out_trans})
            print(self.profile)
            try:
                with rasterio.open(quick_look_path, 'w', **self.profile) as dest:
                    dest.write(mosaic)
            except Exception as e:
                print(e)
            finally:
                for vrt in vrts:
                    vrt.close()
        else:
            print('No DEM tiles were generated.')

    def create_surface(self, shared_dict, val_to_grid, bathy_class, las_path):
        # TODO: Expose pipeline parameters in GUI
        import pdal
        from pathlib import Path

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
                    "output_type": "{val_to_grid}",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                }}
            ]
        }}"""

        try:
            pipeline = pdal.Pipeline(pdal_json)
            __ = pipeline.execute()
            with rasterio.open(vrt_tiff) as src:
                data = src.read()
                profile = src.profile
            shared_dict[vrt_tiff] = [profile, data]
        except Exception as e:
            print(e)

    def create_surface_multiprocess(self, las_paths, num_las, 
                                        val_to_grid, bathy_class):
        shared_dict = mp.Manager().dict()
        p = mp.Pool(int(PROC_CNT / 2))

        # Initialize progress bar so that it shows from onset
        progress('Gen Mean Z', 0, num_las, "pbar")
        func = partial(self.create_surface, shared_dict, 
                       val_to_grid, bathy_class)
        for i, __ in enumerate(p.imap(func, las_paths)):
            time_stamp = datetime.now().isoformat()
            print("{}: {} / {}".format(time_stamp, i + 1, num_las))
            msg_str = f'Generating {val_to_grid} raster'
            progress(msg_str, i + 1, num_las, "pbar")

        return p, shared_dict


def create_quicklook(dir, val_to_grid, bathy_class):
    las_dir = Path(dir)
    las_paths = list(las_dir.glob('*.las'))
    num_las = len(list(las_paths))
    if num_las <= 0:
        print("No las files found")
        exit(1)

    ql = QuickLook()
    p, p_dict = ql.create_surface_multiprocess(las_paths, num_las, val_to_grid, 
                                               bathy_class)
    p.close()
    p.join()

    vrts = [ql.create_src(v) for k, v in p_dict.items()]
    quick_look_path = las_dir / f'QUICK_LOOK_{val_to_grid}.tif'
    ql.gen_mosaic(las_dir, quick_look_path, vrts)
    print('DONE!')


def create_gui():
    val_to_grid = ['mean', 'count']
    bathy_classs = [26, 40]

    layout = [
        [sg.Output(size=(140, 20))],
        [sg.Text('Las directory:', size=(12,1)), 
         sg.In(key='las_dir'), 
         sg.FolderBrowse()],
        [sg.Text('Value to Grid'), 
         sg.Combo(val_to_grid, key='val_to_grid')],
        [sg.Text('Bathymetry Class'), 
         sg.Combo(bathy_classs, key='bathy_class')],
        [sg.Button('Create QLDEM')],
        [sg.Button('EXIT')]
        ]

    window = sg.Window('Quick Look (v1.0.0-rc1)', layout)

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
                                 value['val_to_grid'], 
                                 value['bathy_class'])
            else:
                print("'{}' is not a valid directory".format(value['las_dir']))
    window.Close()
