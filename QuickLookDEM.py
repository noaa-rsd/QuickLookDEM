import os
from pathlib import Path
import pdal 
import rasterio
import rasterio.merge
from tqdm import tqdm
import pathos.pools as pp


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
        gtiff_path = Path(str(las_path).replace('.las', '_QL.tif'))
        gtiff_path = str(gtiff_path).replace('\\', '/')
        pdal_json = """{
            "pipeline":[
                {
                    "type": "readers.las",
                    "filename": """ + '"{}"'.format(las_str) + """
                },
                {
                    "type":"filters.returns",
                    "groups":"last,only"
                },
                {
                    "type":"filters.range",
                    "limits": "Classification[2:2],Classification[26:26]"
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
        p = pp.ProcessPool(4)
        for _ in tqdm(p.imap(self.gen_mean_z_surface, las_paths), 
                      total=num_las_paths, ascii=True):
            pass
        p.close()
        p.join()


def set_gdal_env():
    qchecker_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(qchecker_path)
    user_dir = os.path.expanduser('~')

    script_path = Path(user_dir).joinpath('AppData', 'Local', 'Continuum', 
                                          'anaconda3', 'Scripts')

    gdal_data = Path(user_dir).joinpath('AppData', 'Local', 'Continuum', 
                                        'anaconda3', 'envs', 'QuickLook', 
                                        'Library', 'share', 'gdal')

    proj_lib =Path(user_dir).joinpath('AppData', 'Local', 'Continuum', 
                                      'anaconda3', 'envs', 'QuickLook', 
                                      'Library', 'share')

    if script_path.name not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + str(script_path)

    os.environ["GDAL_DATA"] = str(gdal_data)
    os.environ["PROJ_LIB"] = str(proj_lib)


def main():

    # set_gdal_env()  probably can't use right now, 'cause it relies on specific conda environment

    las_dir = Path(r'V:\FL1703\LIDAR\Classified_LAS')
    las_paths = list(las_dir.glob('*.las'))
    num_las_paths = len(list(las_paths))

    ql = QuickLook()
    ql.gen_mean_z_surface_multiprocess(las_paths, num_las_paths)

    quick_look_path = las_dir / 'QUICK_LOOK.tif'
    ql.gen_mosaic(las_dir, quick_look_path)
        

if __name__ == '__main__':
    main()
