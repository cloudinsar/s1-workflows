#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET

from osgeo import gdal

gdal.UseExceptions()


# xml_path = "/home/emile/openeo/s1-workflows/S1A_SLC_20240809T170739_249435_IW2_VV_440377.SAFE/annotation/s1a-iw2-slc-vv-249435-20240809T170739-440377.xml"
#
# root = ET.parse(xml_path)
# geojson = {
#     "coordinates": [[]],
#     "type": "Polygon"
# }
#
# for elem in root.findall('./geolocationGrid/geolocationGridPointList/geolocationGridPoint'):
#     geojson["coordinates"][0].append([float(elem.find('longitude').text),
#                                       float(elem.find('latitude').text)])
# # TODO: The list of points is not realy a geojson, not sure how to interpret it atm
# with open("geojson_dump.json", "w") as f:
#     json.dump(geojson, f)


def tiff_to_gtiff(input_path, output_path):
    ds_in = gdal.Open(input_path)
    driver = gdal.GetDriverByName("GTiff")
    # Compression is slower, but reduces images from 650Mb to 300Mb for example.
    # Which might save time when transfering to bucket and reading as stac afterwards
    ds_out = driver.CreateCopy(
        output_path, ds_in, options=["TILED=YES", "COMPRESS=DEFLATE"]
    )

    transform = list(ds_in.GetGeoTransform())
    # repr(transform) -> '(0.0, 1.0, 0.0, 0.0, 0.0, 1.0)'
    scale_factor = 180 / 100000  # scal small enough to be visualizable in latlon
    transform[1] *= scale_factor
    transform[5] *= scale_factor

    ds_out.SetGeoTransform(transform)
    ds_out.FlushCache()  # saves to disk
    ds_out = None
    ds = None
