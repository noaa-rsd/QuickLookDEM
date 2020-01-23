import os
from pathlib import Path
import pdal 
import rasterio
import rasterio.merge
from tqdm import tqdm
import pathos.pools as pp


class QuickLook:

    def __init__(self, out_dir):
        self.out_meta = None
        self.out_dir = Path(r'C:\QAQC_contract\TPU_Gridder')

    def get_tile_dems(self, mtype):
        print(f'retreiving individual {mtype} grids...')
        dems = []
        for dem in list(self.out_dir.glob(f'*_{mtype}.tif')):
            print(dem)
            src = rasterio.open(dem)
            dems.append(src)
        self.out_meta = src.meta.copy()  # uses last src made
        return dems

    def gen_mosaic(self, mtype):

        quick_look_path = self.out_dir / f'QUICK_LOOK_{mtype}.tif'

        dems = self.get_tile_dems(mtype)
        if dems:
            print('generating {}...'.format(quick_look_path))
            mosaic, out_trans = rasterio.merge.merge(dems)
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

        gtiff_path_dem = self.out_dir / las_path.name.replace('.las', '_DEM.tif')
        gtiff_path_dem = str(gtiff_path_dem).replace('\\', '/')

        gtiff_path_thu = self.out_dir / las_path.name.replace('.las', '_THU.tif')
        gtiff_path_thu = str(gtiff_path_thu).replace('\\', '/')

        gtiff_path_tvu = self.out_dir / las_path.name.replace('.las', '_TVU.tif')
        gtiff_path_tvu = str(gtiff_path_tvu).replace('\\', '/')

        ##"limits": "Classification[2:2],Classification[26:26]"
        ##{
        ##    "type":"filters.range",
        ##    "limits": "Classification[1:100]"
        ##},

        #pdal_json = """{
        #    "pipeline":[
        #        {
        #            "type": "readers.las",
        #            "filename": """ + '"{}"'.format(las_str) + """
        #        },
        #        {
        #            "type":"filters.returns",
        #            "groups":"last,only"
        #        },
        #        {
        #            "filename": """ + '"{}"'.format(gtiff_path_dem) + """,
        #            "gdaldriver": "GTiff",
        #            "output_type": "mean",
        #            "resolution": "2.0",
        #            "type": "writers.gdal"
        #        }
        #    ]
        #}"""
        
        pdal_json_tpu = """{
            "pipeline":[
                {
                    "type": "readers.las",
                    "filename": """ + '"{}"'.format(las_str) + """,
                    "extra_dims": "total_thu=uint8,total_tvu=uint8",
                    "use_eb_vlr": "true"
                },
                {
                    "type":"filters.range",
                    "limits": "Classification[26:26]"
                },
                {
                    "filename": """ + '"{}"'.format(gtiff_path_thu) + """,
                    "dimension": "total_thu",
                    "gdaldriver": "GTiff",
                    "output_type": "mean",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                },
                {
                    "filename": """ + '"{}"'.format(gtiff_path_tvu) + """,
                    "dimension": "total_tvu",
                    "gdaldriver": "GTiff",
                    "output_type": "mean",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                },
                {
                    "filename": """ + '"{}"'.format(gtiff_path_dem) + """,
                    "gdaldriver": "GTiff",
                    "output_type": "mean",
                    "resolution": "1.0",
                    "type": "writers.gdal"
                }
            ]
        }"""

        try:
            pipeline = pdal.Pipeline(pdal_json_tpu)
            __ = pipeline.execute()
            print(pipeline.arrays['total_thu'])
        except Exception as e:
            print(e)

    def gen_mean_z_surface_multiprocess(self, las_paths):
        p = pp.ProcessPool(4)
        num_las_paths = len(list(las_paths))
        for _ in tqdm(p.imap(self.gen_mean_z_surface, las_paths), 
                      total=num_las_paths, ascii=True):
            pass
        p.close()
        p.join()


def set_env_vars(env_name):
    user_dir = os.path.expanduser('~')
    conda_dir = Path(user_dir).joinpath('AppData', 'Local', 
                                        'Continuum', 'anaconda3')
    env_dir = conda_dir / 'envs' / env_name
    share_dir = env_dir / 'Library' / 'share'
    script_path = conda_dir / 'Scripts'
    gdal_data_path = share_dir / 'gdal'
    proj_lib_path = share_dir

    if script_path.name not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + str(script_path)
    os.environ["GDAL_DATA"] = str(gdal_data_path)
    os.environ["PROJ_LIB"] = str(proj_lib_path)


def main():

    set_env_vars('shore_att')

    las_dir = Path(r'T:\2017\MD1702-TB-N_Jeromes_Creek_p\06_RIEGL_PROC\04_EXPORT\Green\04_MD1702-TB-N_g_gpsa_rf_ip_wsf_r_adj_cls_fnl_tpu')
    las_paths = list(las_dir.glob('*.las'))

    out_dir = Path(r'C:\QAQC_contract\TPU_Gridder')

    ql = QuickLook(out_dir)
    #ql.gen_mean_z_surface_multiprocess(las_paths)

    ql.gen_mosaic('DEM')
    ql.gen_mosaic('THU')
    ql.gen_mosaic('TVU')
        

if __name__ == '__main__':
    main()
