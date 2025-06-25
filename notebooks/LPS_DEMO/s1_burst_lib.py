import urllib
import json

import folium
from folium.plugins.treelayercontrol import TreeLayerControl

from shapely import from_wkt

import numpy as np
import pandas as pd

import calendar

import matplotlib.pyplot as plt

import esa_snappy as snappy

import os
import boto3
from pathlib import Path

from dateutil.parser import parse
import datetime


def retrieve_bursts(start_date, end_date, pol, aoi):

    https_request = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Bursts?$filter=" + urllib.parse.quote(
        f"ContentDate/Start ge {start_date}T00:00:00.000Z and ContentDate/Start le {end_date}T23:59:59.000Z and "
        f"PolarisationChannels eq '{pol}' and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{aoi}')"
    ) + "&$top=1000"

    with urllib.request.urlopen(https_request) as response:
        content = response.read().decode()
        
    return json.loads(content)


def show_bursts(bursts, aoi):

    bursts_uniqueTrack = {}
    burstId_list = []
    track_list = []
    for b in bursts['value']:
        if b['RelativeOrbitNumber'] not in track_list:
            bursts_uniqueTrack[b['RelativeOrbitNumber']] = {}
            track_list.append(b['RelativeOrbitNumber'])
        burstId_subswath = f"BurstId: {b['BurstId']}, {b['SwathIdentifier']}"
        if burstId_subswath not in burstId_list:
            bursts_uniqueTrack[b['RelativeOrbitNumber']][burstId_subswath] = b['GeoFootprint']['coordinates']
            burstId_list.append(burstId_subswath)

    lat, lon = [], []
    for burst in bursts_uniqueTrack.values():
        for coords in burst.values():
            lat = lat + [c[1] for c in coords[0]]
            lon = lon + [c[0] for c in coords[0]]
    
    m = folium.Map(
        location=[np.mean([max(lat), min(lat)]), np.mean([max(lon), min(lon)])],
        zoom_start=8
    )
    
    # Add the area of interest
    geom = from_wkt(aoi)
    
    if geom.geom_type == 'Point':
        folium.Marker([geom.y, geom.x]).add_to(m)
    
    if geom.geom_type == 'Polygon':
        folium.Polygon(
            locations=[(y, x) for x, y in geom.exterior.coords],
            color='blue',
            fill=True,            
            fill_color='blue',    
            fill_opacity=0.4
        ).add_to(m)
    
    
    # Add each burst grouped by track
    children = []
    for track, burst in bursts_uniqueTrack.items():
        children.append(
            {
                "label": f"Track {track}",
                "select_all_checkbox": True,
                "children": [{"label":str(b), "layer": folium.Polygon(locations=np.flip(np.squeeze(p), axis=1), color='red').add_to(m)} for b, p in burst.items()]
            }
        )
    
    # Show the map
    overlay_tree = {
        "label": "Burst Footprints",
        "select_all_checkbox": "Un/select all",
        "children": children
    }
    
    TreeLayerControl(overlay_tree=overlay_tree).add_to(m)
    return m


def display_calendar(year, month, highlighted_dates={}):

    cal = calendar.monthcalendar(year, month)
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.set_xticks([])
    ax.set_yticks([])
                
    for row, week in enumerate(cal):
        for col, day in enumerate(week):
            if day == 0:
                continue
            color = highlighted_dates.get(day, "white")
            ax.add_patch(plt.Rectangle((col - 0.5, row - 0.5), 1, 1, color=color, alpha=0.6))
            ax.text(col, row, str(day), ha="center", va="center", fontsize=12, weight='bold')

    ax.set_xlim(-0.5, 6.5)
    ax.set_ylim(len(cal) - 0.5, -0.5)
    ax.set_title(calendar.month_name[month] + f" {year}")
    plt.show()


def show_acquisition_calendar(bursts):

    date, track = [], [] 
    for b in bursts['value']:
        date.append(b['BeginningDateTime'])
        track.append(b['RelativeOrbitNumber'])
    df = pd.DataFrame(data={'date': date, 'track': track})
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    df = df.drop_duplicates(subset=['track', 'year', 'month', 'day'])
    df = df.sort_values(by='date', ascending=True)

    color_track = {}
    fig, ax = plt.subplots(figsize=(4, len(df['track'].unique())*0.5))
    for i, t in enumerate(df['track'].unique()):
        color_track[t] = f'C{i}'
        ax.add_patch(plt.Rectangle((0, -i*0.5), 0.1, 0.3, color=color_track[t], alpha=0.6))
        ax.text(0.15, -i*0.5+0.1, f'T{t}', fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(-len(df['track'].unique())*0.5, 0.5)
    ax.axis('off')
    plt.show()
    
    for year in df['year'].unique():
        df_year = df.loc[df['year'] == year, :]
        for month in df_year['month'].unique():
            h = {}
            for i, row in df_year.loc[df_year['month'] == month, :].iterrows():
                h[row['day']] = color_track[row['track']]
            display_calendar(year, month, h)


def download_s1metadata(bursts, sub_swath_identifier, burst_id, CDSE_ACCESS_KEY, CDSE_SECRET_KEY):
    
    SAFE_image_list = []
    S3_image_list = []
    for b in bursts['value']:
        if b['SwathIdentifier'].lower() == sub_swath_identifier:
            if str(b["BurstId"]) == str(burst_id):
                if b["ParentProductName"] not in SAFE_image_list:
                    SAFE_image_list.append((b["ParentProductName"]))
                    S3_image_list.append((b["S3Path"].split(".SAFE")[0] + ".SAFE"))


    polarization = bursts['value'][0]['PolarisationChannels']
    if polarization.lower()=="vv":
        include_pol='vv'
        exclude_pol='vh'
    elif polarization.lower()=="vh":
        include_pol='vh'
        exclude_pol='vv'
    
    s3_endpoint = "https://eodata.dataspace.copernicus.eu"
    
    s3_resource=boto3.resource(
        's3',
        aws_access_key_id=CDSE_ACCESS_KEY,
        aws_secret_access_key=CDSE_SECRET_KEY,
        endpoint_url=s3_endpoint
    )
    client = s3_resource.meta.client
    bucket_name = "eodata"
    bucket=s3_resource.Bucket(bucket_name)
    
    for im_safe, im_s3 in zip(SAFE_image_list,S3_image_list):
        safe_files = bucket.objects.filter(Prefix=im_s3[8:])
        for file in safe_files:
            if (sub_swath_identifier.lower() in file.key and include_pol in file.key) or "manifest.safe" in file.key:
                output_path = "S1" + file.key.split("S1")[1]
                # Create output directory structure
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                if ".tiff" in file.key:
                    command = f"gdal_create -ot Int8 -outsize 1 1 -bands 1 -burn 0 {output_path}"
                    os.system(command)
                    continue
                client.download_file(bucket_name, file.key, output_path)

    return SAFE_image_list


def compute_baseline(SAFE_image_list):

    products = []
    for im in SAFE_image_list:
        products.append(snappy.ProductIO.readProduct(im))
    
    # import the stack operator
    create_stack = snappy.jpy.get_type('eu.esa.sar.insar.gpf.coregistration.CreateStackOp')
    # 1st argument: list of products between which you want to compute the baseline
    # 2nd argument: a product that will receive the baselines as new metadata
    master = products[0]
    create_stack.getBaselines(products, master)
    # Now there is a new piece of metadata in product one called 'Baselines'
    baseline_root_metadata = master.getMetadataRoot().getElement('Abstracted_Metadata').getElement('Baselines')
    # You can now display all the baselines between all master/slave configurations
    master_ids = list(baseline_root_metadata.getElementNames())
    master_dates = []
    slave_dates = []
    perpendicular_baselines = []
    delta_times = []
    for master_id in master_ids:
        slave_ids = list( baseline_root_metadata.getElement(master_id).getElementNames())
        for slave_id in slave_ids:
            # print(f'{master_id}, {slave_id}')
            snap_date_mst = master_id.split("_")[1]
            date_obj_mst = parse(snap_date_mst)
            snap_date_slv = slave_id.split("_")[1]
            date_obj_slv = parse(snap_date_slv)
            
            delta_time = date_obj_mst - date_obj_slv
            # if delta_time == datetime.timedelta(0):
                # continue
            master_dates.append(date_obj_mst)
            slave_dates.append(date_obj_slv)
            delta_times.append(delta_time)
            baseline_metadata = baseline_root_metadata.getElement(master_id).getElement(slave_id)
            for baseline in list(baseline_metadata.getAttributeNames()):
                if baseline == "Perp Baseline":
                    perpendicular_baseline = baseline_metadata.getAttributeString(baseline)
                    perpendicular_baselines.append(perpendicular_baseline)
                    #print(f'{baseline}: {perpendicular_baseline}')

    return pd.DataFrame([[a,b,float(c),d] for a,b,c,d in zip(master_dates,slave_dates,perpendicular_baselines,delta_times)], columns=["master_date","slave_date","perp_baseline","temp_baseline"])


def find_optimal_master(SAFE_image_list):

    products = []
    for im in SAFE_image_list:
        products.append(snappy.ProductIO.readProduct(im))
    InSARStackOverview = snappy.jpy.get_type('eu.esa.sar.insar.gpf.InSARStackOverview')
    return InSARStackOverview.findOptimalMasterProduct(products).getName()
  

def sbas_pairs(SAFE_image_list, max_temporal_baseline, max_perp_baseline):

    df = compute_baseline(SAFE_image_list)
    optimal_master = find_optimal_master(SAFE_image_list)

    zero_reference_date = optimal_master.split("_")[5][:4] + "-" + optimal_master.split("_")[5][4:6] + "-" + optimal_master.split("_")[5][6:8]
    
    filter_mask = np.bitwise_and(abs(df["temp_baseline"])<=datetime.timedelta(max_temporal_baseline),abs(df["perp_baseline"])<=max_perp_baseline)
    df_filtered = df[filter_mask].reset_index()

    ax = df[df["master_date"]==zero_reference_date].plot.scatter(
        x='slave_date',
        y='perp_baseline',
        color="red",
        ylim=(-500, 500))
    for x in df_filtered.index:
        single = df_filtered.iloc[[x]]
        point_1 = df[np.bitwise_and(df["master_date"]==zero_reference_date,np.bitwise_or(df["slave_date"]==single["master_date"].values[0],df["slave_date"]==single["slave_date"].values[0]))]
        ax = point_1.plot.line(
                x='slave_date',
                y='perp_baseline',
                legend=False,
                ax=ax,
                color="blue",
                linewidth=0.1)
    plt.show()

    return df_filtered.assign(
        master_date_str=df_filtered['master_date'].dt.strftime('%Y-%m-%d'),
        slave_date_str=df_filtered['slave_date'].dt.strftime('%Y-%m-%d')
    )[['master_date_str', 'slave_date_str']].values.tolist()



def ps_pairs(SAFE_image_list):

    df = compute_baseline(SAFE_image_list)
    optimal_master = find_optimal_master(SAFE_image_list)

    zero_reference_date = optimal_master.split("_")[5][:4] + "-" + optimal_master.split("_")[5][4:6] + "-" + optimal_master.split("_")[5][6:8]

    df_filtered_ = df[df["master_date"]==zero_reference_date].reset_index()
    ax = df[df["master_date"]==zero_reference_date].plot.scatter(
        x='slave_date',
        y='perp_baseline',
        color="red",
        ylim=(-500, 500))
    for x in df_filtered_.index:
        single = df_filtered_.iloc[[x]]
        point_1 = df[np.bitwise_and(df["master_date"]==zero_reference_date,np.bitwise_or(df["slave_date"]==single["master_date"].values[0],df["slave_date"]==single["slave_date"].values[0]))]
        ax = point_1.plot.line(
                x='slave_date',
                y='perp_baseline',
                legend=False,
                ax=ax,
                color="blue",
                linewidth=0.1)
    plt.show()

    return df_filtered_.assign(
        master_date_str=df_filtered_['master_date'].dt.strftime('%Y-%m-%d'),
        slave_date_str=df_filtered_['slave_date'].dt.strftime('%Y-%m-%d')
    )[['master_date_str', 'slave_date_str']].values.tolist()
    

