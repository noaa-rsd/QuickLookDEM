import os
import logging
from pathlib import Path
import rasterio
import rasterio.merge
import multiprocessing as mp
from PySimpleGUI import OneLineProgressMeter as progress
from tqdm import tqdm


class QuickLook:

    def __init__(self):
        self.dems = []
        self.out_meta = None

    def get_tile_dems(self, dem_dir):
        print('retreiving individual QL DEMs...')
        for dem in list(dem_dir.glob('*_QL.tif')):
            src = rasterio.open(dem)
            self.dems.append(src)
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
        import pdal
        from pathlib import Path

        las_str = str(las_path).replace('\\', '/')
        gtiff_path = Path(str(las_path).replace('.laz', '_QL.tif'))
        gtiff_path = str(gtiff_path).replace('\\', '/')
        pdal_json = f"""{{
                    "pipeline":[
                        {{
                            "type": "readers.las",
                            "filename": "{las_str}"
                        }},
                        {{
                            "type":"filters.range",
                            "limits": "Classification[40:40]"
                        }},
                        {{
                            "filename": "{gtiff_path}",
                            "gdaldriver": "GTiff",
                            "output_type": "count",
                            "resolution": "1.0",
                            "type": "writers.gdal"
                        }}
                    ]
                }}"""

        try:
            pipeline = pdal.Pipeline(pdal_json)
            __ = pipeline.execute()
        except Exception as e:
            print(e)

    def gen_mean_z_surface_multiprocess(self, las_paths, num_las_paths):
        p = mp.Pool(processes=4)
        for _ in tqdm(p.imap_unordered(self.gen_mean_z_surface, las_paths), 
                      total=num_las_paths, ascii=True):
            pass
        p.close()
        p.join()
   

if __name__ == '__main__':

    las_dir = Path(r'X:\2018\FL1806\Lidar\TPU\Block02\TPU_LAS_no_mcu')

    las_paths = list(las_dir.glob('*.las'))
    print(las_paths)
    num_las_paths = len(list(las_paths))

    ql = QuickLook()
    ql.gen_mean_z_surface_multiprocess(las_paths, num_las_paths)

    quick_look_path = las_dir / 'QUICK_LOOK.tif'
    ql.gen_mosaic(las_dir, quick_look_path)
