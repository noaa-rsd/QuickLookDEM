class Mosaic:

    def __init__(self, mtype, config):
        self.mtype = mtype
        self.config = config
        self.mosaic_dataset_base_name = r'{}_{}_mosaic'.format(self.config.project_name, self.mtype)
        self.mosaic_dataset_path = Path(self.config.mosaics_to_make[self.mtype][1]) / '{}.tif'.format(self.mosaic_dataset_base_name)
        self.source_dems_dir = Path(self.config.surfaces_to_make[self.mtype][1])
        self.dems = []
        self.src = None
        self.out_meta = None

    def get_tile_dems(self):
        print('retreiving individual {} tiles...'.format(self.mtype))
        for dem in list(self.source_dems_dir.glob('*_{}.tif'.format(self.mtype.upper()))):
            #print('retreiving {}...'.format(dem))
            src = rasterio.open(dem)
            self.dems.append(src)

        self.out_meta = src.meta.copy()  # uses last src made

    def gen_mosaic(self):
        self.get_tile_dems()

        if self.dems:
            print('generating {}...'.format(self.mosaic_dataset_path))
            mosaic, out_trans = rasterio.merge.merge(self.dems)

            self.out_meta.update({
                'driver': "GTiff",
                'height': mosaic.shape[1],
                'width': mosaic.shape[2],
                'transform': out_trans})

            # save mosaic DEMs
            with rasterio.open(self.mosaic_dataset_path, 'w', **self.out_meta) as dest:
                dest.write(mosaic)
        else:
            print('No DEM tiles were generated.')
            

class Surface:

    def __init__(self, tile, stype, config):
        self.stype = stype
        self.las_path = tile.path
        self.las_name = tile.name
        self.las_str = tile.las_str
        self.las_extents = tile.las_extents
        self.config = config
        self.tile = tile

    def __str__(self):
        return self.raster_path[self.stype]

    def create_dz_dem(self):
        
        def gen_pipeline(gtiff_path, las_bounds):
            pdal_json = """{
                "pipeline":[
                    {
                        "type": "readers.las",
                        "filename": """ + '"{}"'.format(self.las_str) + """
                    },
                    {
                        "type":"filters.range",
                        "limits": "Classification[2:2],Classification[26:26]" 
                    },
                    {
                        "type":"filters.returns",
                        "groups":"last,only"
                    },
                    {
                        "type":"filters.groupby",
                        "dimension":"PointSourceId"
                    },
                    {
                        "type": "writers.gdal",
                        "gdaldriver": "GTiff",
                        "output_type": "mean",
                        "resolution": "1.0",
                        "bounds": """ + '"{}",'.format(las_bounds) + """
                        "filename":  """ + '"{}"'.format(gtiff_path) + """
                    }
                ]
            }"""

            return pdal_json

        def create_dz(las_name):

            tif_dir = Path(self.config.surfaces_to_make[self.stype][1])

            tifs = []
            meta = None
            for t in tif_dir.glob('{}*.tif'.format(las_name)):
                with rasterio.open(t, 'r') as tif:
                    tifs.append(tif.read(1))

                    if not meta:
                        meta = tif.meta.copy()

                os.remove(t)

            if tifs:  # sometimes tif isn't made for las having ground or bathy (one e.g. was las having only 3 class 26 pts)
                tifs = np.stack(tifs, axis=0)
                tifs[tifs == -9999] = np.nan
                tifs = np.nanmax(tifs, axis=0) - np.nanmin(tifs, axis=0)
                tifs[(np.isnan(tifs)) | (tifs == 0)] = -9999

                dz_path = '{}\{}_DZ.tif'.format(self.config.surfaces_to_make[self.stype][1], self.las_name)
                with rasterio.open(dz_path, 'w', **meta) as dz:
                    dz.write(np.expand_dims(tifs, axis=0))
            else:
                print('{} has no tifs :(...'.format(self.las_name))

        cmd_str = 'pdal info {} --summary'.format(self.las_str)
        stats = self.tile.run_console_cmd(cmd_str)[1]
        stats_dict = json.loads(stats)

        bounds = stats_dict['summary']['bounds']
        minx = bounds['minx']
        maxx = bounds['maxx']
        miny = bounds['miny']
        maxy = bounds['maxy']
        las_bounds = ([minx,maxx],[miny,maxy])

        gtiff_path = r'{}\{}_PSI_#.tif'.format(self.config.surfaces_to_make[self.stype][1], self.las_name)
        gtiff_path = str(gtiff_path).replace('\\', '/')
        
        print('generating {} surface for {}...'.format(self.stype, self.las_name))
        pipeline = pdal.Pipeline(gen_pipeline(gtiff_path, las_bounds))
        __ = pipeline.execute()

        create_dz(self.las_name)

    def gen_mean_z_surface(self, dem_type):
        las_str = str(self.las_path).replace('\\', '/')
        gtiff_path = r'{}\{}_{}.tif'.format(self.config.surfaces_to_make[self.stype][1], self.las_name, self.stype)
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
                    "output_type": """ + '"{}"'.format(dem_type) + """,
                    "resolution": "1.0",
                    "type": "writers.gdal"
                }
            ]
        }"""

        print('generating {} surface for {}...'.format(self.stype, self.las_name))

        try:
            pipeline = pdal.Pipeline(pdal_json)
            count = pipeline.execute()
        except Exception as e:
            print(e)
        pass