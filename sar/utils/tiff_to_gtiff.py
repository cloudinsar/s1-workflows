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


def tiff_to_gtiff(input_path, output_path, tiff_per_band=False) -> list:
    input_path = Path(input_path)
    print(f"tiff_to_gtiff({input_path=})")
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

    transform_in = list(ds_in.GetGeoTransform())
    print(f"{transform_in=}")  # [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    # TODO: Avoid: "The offset of the first block of the image should be after its IFD"
    driver_tiff = gdal.GetDriverByName("GTiff")  # COG GTiff

    output_paths = []
    if tiff_per_band:
        assert "<band_name>" in output_path, "When tiff_per_band is True, output_path should contain '<band_name>'"
        # No need to write the inbetween image to disk
        driver = gdal.GetDriverByName('MEM')
        ds_out = driver.CreateCopy(output_path, ds_in)
    else:
        # Compression is slower, but reduces images from 650Mb to 300Mb for example.
        # Which might save time when transferring to bucket and reading as stac afterward
        ds_out = driver_tiff.CreateCopy(output_path, ds_in, options=["TILED=YES", "COMPRESS=DEFLATE"])
        # ds_out.BuildOverviews("NONE", overviewlist=[])  # TODO: remove overviews?
        output_paths.append(output_path)

    for i in range(1, ds_out.RasterCount + 1):
        band = ds_out.GetRasterBand(i)
        band.SetDescription(band_names[i - 1])

    projection_in: str = ds_in.GetProjection()
    if (
            '["EPSG","4326"]' in projection_in  # default
            and transform_in == [0.0, 1.0, 0.0, 0.0, 0.0, 1.0]  # meaning no geotransform
            and (ds_in.RasterXSize > 360 or ds_in.RasterYSize > 90)
    ):
        # set CRS to webmercator, to avoid pixels going out of the CRS bounds:
        ds_out.SetProjection("EPSG:3857")
        # TODO: Remove GeoTiePoints

    ds_out.SetGeoTransform(transform_in)
    ds_out.FlushCache()  # saves to disk if not in memory

    if tiff_per_band:
        for i in range(1, ds_out.RasterCount + 1):
            band_name = band_names[i - 1]
            band_tmp = ds_out.GetRasterBand(i)
            output_path_band = output_path.replace("<band_name>", band_name)
            output_paths.append(output_path_band)
            ds_single = driver_tiff.Create(
                output_path_band,
                band_tmp.XSize,
                band_tmp.YSize,
                1,
                band_tmp.DataType,
                options = ["TILED=YES", "COMPRESS=DEFLATE"],
            )
            ds_single.SetProjection(ds_out.GetProjection())
            ds_single.SetSpatialRef(ds_out.GetSpatialRef())
            ds_single.SetGeoTransform(ds_out.GetGeoTransform())
            ds_single.SetStyleTable(ds_out.GetStyleTable())

            ds_single_band = ds_single.GetRasterBand(1)
            ds_single_band.WriteArray(band_tmp.ReadAsArray())
            ds_single_band.SetDescription(band_tmp.GetDescription())

            ds_single_band.FlushCache()

            ds_single.FlushCache()  # saves to disk
    return output_paths


if __name__ == "__main__":
    from tests.testutils import assert_tif_file_is_healthy

    # assert_tif_file_is_healthy("tmp_prm_20180128T062713.tif")
    tiff_to_gtiff(
        # "S1_coh_2images_20240821T170739_20240902T170739.tif",
        # "S1_coh_2images_20240821T170739_20240902T170739.test.tif",
        "tmp_sec_20240821T055907.tif",
        "tmp_sec_20240821T055907_<band_name>.tif",
    )
    # assert_tif_file_is_healthy("tmp_prm_20180128T062713.test.tif")
