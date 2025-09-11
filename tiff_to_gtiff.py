#!/usr/bin/env python3
import os.path
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import exifread
from osgeo import gdal, gdalconst

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
# # TODO: The list of points is not really a geojson, not sure how to interpret it atm
# with open("tmp_geojson_dump.json", "w") as f:
#     json.dump(geojson, f)


def tiff_to_gtiff(input_paths, output_path, band_names=[]):
    if type(input_paths)==str:
        input_paths = [input_paths]

    projection_in = None
    xsize = None
    ysize = None
    total_bands = 0
    rasters = []
    for input_path in input_paths:

        input_path = Path(input_path)
        print(f"tiff_to_gtiff {input_path=}")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file {input_path} does not exist.")

        with input_path.open("rb") as f:
            tags = exifread.process_file(f)
            tag = next(filter(lambda x: x.tag == 65000, tags.values()), None)
            if tag:
                xml_str = tag.values
                root = ET.fromstring(xml_str)
                band_tags = root.findall(".//Image_Interpretation/Spectral_Band_Info")
                band_tags.sort(key=lambda x: int(x.find("BAND_INDEX").text))
                date_suffix_regex = re.compile(
                    r"_IW\d_(?P<polarization>\w\w)(_\w\w\w\w?)?_\d\d[A-Z]\w+\d\d\d\d(_\d\d[A-Z]\w+\d\d\d\d)?$"
                )
                dates_regex = re.compile(r"_\d\d[A-Z]\w{1,4}\d\d\d\d")
                grid_regex = re.compile(r"^(?P<matchgroup>\w+)_band$")

                def tag_to_band_name(band_tag):
                    band_name = band_tag.find("BAND_NAME").text
                    band_name = date_suffix_regex.sub(r"_\g<polarization>", band_name)
                    band_name = dates_regex.sub("", band_name)
                    band_name = grid_regex.sub(r"grid_\g<matchgroup>", band_name)
                    return band_name

                band_names.append(list(map(tag_to_band_name, band_tags)))

        ds = gdal.Open(input_path, gdal.GA_ReadOnly)
        rasters.append(ds)
        if projection_in is None:
            projection_in: str = ds.GetProjection()
            transform = list(ds.GetGeoTransform())
            xsize = ds.RasterXSize
            ysize = ds.RasterYSize
        total_bands = total_bands + ds.RasterCount


    # Create output with 4 bands (assuming float32, but adjust as needed)
    driver = gdal.GetDriverByName("GTiff")
    ds_out = driver.Create(output_path, xsize, ysize, total_bands, gdal.GDT_Float32, options=["TILED=YES", "COMPRESS=DEFLATE"])
    if (
        '["EPSG","4326"]' in projection_in
        and transform == [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        and (xsize > 360 or ysize > 90)
    ):
        # set CRS to webmercator, to avoid pixels going out of the CRS bounds:
        ds_out.SetProjection("EPSG:3857")
    ds_out.SetGeoTransform(transform)

    band_num = 0
    for i,ds in enumerate(rasters):
        for j in range(ds.RasterCount):
            band_in = ds.GetRasterBand(j+1).ReadAsArray()

            band_out = ds_out.GetRasterBand(band_num+1)
            band_out.SetDescription(band_names[i][j])
            band_out.WriteArray(band_in)
            band_num += 1
            
    # Flush to disk
    ds_out.FlushCache()
    ds_out = None


if __name__ == "__main__":
    tiff_to_gtiff(
        ["tmp_slv_20240902T170739_vh.tif","tmp_slv_20240902T170739_vv.tif"], #TODO: the order of the bands is important
        "S1_2images_20240902T170739.tif",
        # "tmp_mst_20180128T062713.tif",
        # "tmp_mst_20180128T062713.test.tif",
        band_names=[],
    )
