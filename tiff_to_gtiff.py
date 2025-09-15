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


def tiff_to_gtiff(input_path, output_path, band_names=None):
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

            band_names = list(map(tag_to_band_name, band_tags))

    ds_in = gdal.Open(str(input_path), gdalconst.GA_ReadOnly)

    transform = list(ds_in.GetGeoTransform())
    # print(repr(transform))  # [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

    driver = gdal.GetDriverByName("GTiff")
    # Compression is slower, but reduces images from 650Mb to 300Mb for example.
    # Which might save time when transfering to bucket and reading as stac afterwards
    ds_out = driver.CreateCopy(
        output_path, ds_in, options=["TILED=YES", "COMPRESS=DEFLATE"]
    )

    if band_names:
        for i in range(1, ds_out.RasterCount + 1):
            band = ds_out.GetRasterBand(i)
            band.SetDescription(band_names[i - 1])

    projection_in: str = ds_in.GetProjection()
    if (
        '["EPSG","4326"]' in projection_in
        and transform == [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        and (ds_in.RasterXSize > 360 or ds_in.RasterYSize > 90)
    ):
        # set CRS to webmercator, to avoid pixels going out of the CRS bounds:
        ds_out.SetProjection("EPSG:3857")

    ds_out.SetGeoTransform(transform)
    ds_out.FlushCache()  # saves to disk


if __name__ == "__main__":
    tiff_to_gtiff(
        "S1_coh_2images_20240821T170739_20240902T170739.tif",
        "S1_coh_2images_20240821T170739_20240902T170739.test.tif",
        # "tmp_mst_20180128T062713.tif",
        # "tmp_mst_20180128T062713.test.tif",
        band_names=[""],
    )
