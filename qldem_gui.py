import os
import time
import multiprocessing as mp
from pathlib import Path
import rasterio
import rasterio.merge
import PySimpleGUI as sg
import pathos
import pathos.pools as pp

os.environ["PYTHONUNBUFFERED"] = "1"

"""Multiprocessing variables"""
PROC_CNT = mp.cpu_count()
PROC_NAME = "{}_{}".format(mp.current_process().name, os.getpid())


class QuickLook:

    def __init__(self):
        self.dems = []
        self.out_meta = None

    def get_tile_dems(self, dem_dir):
        print('retrieving individual QL DEMs...')
        num_dems = len(list(dem_dir.glob('*_QL.tif')))
        for cnt, dem in enumerate(list(dem_dir.glob('*_QL.tif'))):
            src = rasterio.open(dem)
            self.dems.append(src)
            sg.OneLineProgressMeter('Retrieve QL DEMs', cnt + 1, num_dems, "dbar")
        self.out_meta = src.meta.copy()  # uses last src made

    def gen_mosaic(self, dem_dir, quick_look_path):
        self.get_tile_dems(dem_dir)
        if self.dems:
            print('generating {}...'.format(quick_look_path))
            mosaic, out_trans = rasterio.merge.merge(self.dems)
            self.out_meta.update({
                'driver': "GTiff",
                'height': mosaic.shape[1],
                'width': mosaic.shape[2],
                'transform': out_trans})

            with rasterio.open(quick_look_path, 'w', **self.out_meta) as dest:
                dest.write(mosaic)
        else:
            print('No DEM tiles were generated.')

    def gen_mean_z_surface(self, las_path):
        # TODO: Expose pipeline parameters in GUI
        import pdal
        from pathlib import Path

        las_str = str(las_path).replace('\\', '/')
        gtiff_path = Path(str(las_path).replace('.las', '_QL.tif'))
        gtiff_path = str(gtiff_path).replace('\\', '/')
        pdal_json = """{
            "pipeline":[
                {
                    "type": "readers.las",
                    "filename": """ + '"{}"'.format(las_str) + """
                },
                {
                    "type": "filters.outlier",
                    "method": "statistical",
                    "mean_k": 3,
                    "multiplier": 1.2
                },
                {
                    "type":"filters.range",
                    "limits": "Classification[0:1]"
                },
                {
                    "filename": """ + '"{}"'.format(gtiff_path) + """,
                    "gdaldriver": "GTiff",
                    "output_type": "mean",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                }
            ]
        }"""

        try:
            pipeline = pdal.Pipeline(pdal_json)
            __ = pipeline.execute()
        except Exception as e:
            print(e)

    def gen_mean_z_surface_multiprocess(self, las_paths, num_las_paths):
        p = pp.ProcessPool(PROC_CNT - 1)

        # Initialize progress bar so that it shows from onset
        sg.OneLineProgressMeter('Gen Mean Z', 0, num_las_paths, "pbar")

        for num in enumerate(p.imap(self.gen_mean_z_surface, las_paths)):
            print("\n<{}> #{}: {} / {}".format(PROC_NAME, time.strftime("%X %x"), num[0] + 1, num_las_paths))
            sg.OneLineProgressMeter('Gen Mean Z', num[0] + 1, num_las_paths, "pbar")

        p.close()
        p.join()


def create_quicklook(dir):
    las_dir = Path(dir)
    las_paths = list(las_dir.glob('*.las'))
    num_las_paths = len(list(las_paths))
    if num_las_paths <= 0:
        print("No las files found")
        exit(1)

    ql = QuickLook()
    ql.gen_mean_z_surface_multiprocess(las_paths, num_las_paths)

    quick_look_path = las_dir / 'QUICK_LOOK.tif'
    ql.gen_mosaic(las_dir, quick_look_path)


def create_gui():
    layout = [
        [sg.Output(size=(140, 20))],
        [sg.Text('Las directory:', size=(12,1)), sg.In(key='las_dir'), sg.FolderBrowse()],
        [sg.Button('Create QLDEM')],
        [sg.Button('EXIT')]
    ]

    window = sg.Window('Quicklook DEM Generator', layout)

    return window

    
if __name__ == '__main__':
    # Required for pyinstaller support of multiprocessing
    pathos.helpers.freeze_support()

    window = create_gui()

    while True:      
        (event, value) = window.Read() 
        #print(event, value)
        if event == 'EXIT'  or event is None:      
            break # exit button clicked    
        elif event == 'Create QLDEM':      
            print(value['las_dir'])
            if os.path.isdir(value['las_dir']):
                create_quicklook(value['las_dir'])
            else:
                print("'{}' is not a valid directory".format(value['las_dir']))
    window.Close()
