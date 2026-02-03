"""
Data loading utilities for Urban Climate Explorer
Loads data from AWS S3 bucket for Streamlit Cloud deployment
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
import xarray as xr
import numpy as np
from pathlib import Path
import os
import tempfile
import requests
from io import BytesIO

# S3 Configuration - Public bucket URLs
S3_BUCKET = "amzn-uhiumiresearchbucket"
S3_REGION = "us-east-1"
S3_BASE_URL = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/Data"

# Fallback to local paths for development
APP_PATH = Path(__file__).parent.parent
BASE_PATH = APP_PATH.parent
USE_S3 = True  # Set to False for local development

def get_s3_url(path):
    """Get full S3 URL for a given path"""
    return f"{S3_BASE_URL}/{path}"

@st.cache_data(ttl=3600)  # Cache for 1 hour
def download_file_to_memory(url):
    """Download a file from URL to memory"""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return BytesIO(response.content)

@st.cache_data(ttl=3600)
def download_shapefile_components(base_name, s3_folder="shp"):
    """
    Download all shapefile components to a temp directory.
    Returns path to the .shp file.
    """
    extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg']
    temp_dir = tempfile.mkdtemp()
    
    for ext in extensions:
        url = get_s3_url(f"{s3_folder}/{base_name}{ext}")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                file_path = os.path.join(temp_dir, f"{base_name}{ext}")
                with open(file_path, 'wb') as f:
                    f.write(response.content)
        except requests.RequestException:
            # Some extensions like .cpg may not exist, that's okay
            pass
    
    return os.path.join(temp_dir, f"{base_name}.shp")

@st.cache_data
def load_analysis_data():
    """Load the pre-computed analysis CSV with SUHI/UMI metrics"""
    if USE_S3:
        csv_url = get_s3_url("csv/All_50_Cities_Analysis_Summary.csv")
        df = pd.read_csv(csv_url)
    else:
        csv_path = APP_PATH / "csv" / "All_50_Cities_Analysis_Summary.csv"
        df = pd.read_csv(csv_path)
    
    # Rename columns for clarity
    df = df.rename(columns={'LCZ': 'LCZ_Class'})
    # Calculate UDI as negative UMI
    df['UDI'] = -df['UMI']
    return df

@st.cache_data
def load_city_boundaries():
    """Load city boundaries shapefile with attributes"""
    if USE_S3:
        shp_path = download_shapefile_components("Top50_Cities_Urban_Boundaries_Matched")
    else:
        shp_path = BASE_PATH / "Data" / "shp" / "Top50_Cities_Urban_Boundaries_Matched.shp"
    
    gdf = gpd.read_file(shp_path)
    # Ensure WGS84 for web mapping
    gdf = gdf.to_crs(epsg=4326)
    return gdf

@st.cache_data
def load_conus_states():
    """Load CONUS state boundaries"""
    if USE_S3:
        shp_path = download_shapefile_components("CONUS_state_wgs")
    else:
        shp_path = BASE_PATH / "Data" / "shp" / "CONUS_state_wgs.shp"
    
    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs(epsg=4326)
    return gdf

@st.cache_data
def load_regions():
    """Load US Census regions shapefile"""
    if USE_S3:
        shp_path = download_shapefile_components("cb_2024_us_region_500k")
    else:
        shp_path = BASE_PATH / "Data" / "shp" / "cb_2024_us_region_500k.shp"
    
    gdf = gpd.read_file(shp_path)
    gdf = gdf.to_crs(epsg=4326)
    return gdf

@st.cache_resource
def load_netcdf():
    """Load NetCDF climate data (lazy loading from S3 or local)"""
    if USE_S3:
        # For NetCDF files, we need to download to temp file first
        # as xarray doesn't directly support HTTP for all operations
        nc_url = get_s3_url("raster/CONUS_Climate_Data_1km.nc")
        
        # Check if file is already cached in temp
        temp_dir = tempfile.gettempdir()
        cached_path = os.path.join(temp_dir, "CONUS_Climate_Data_1km.nc")
        
        if not os.path.exists(cached_path):
            st.info("Downloading climate data (this may take a moment on first load)...")
            response = requests.get(nc_url, timeout=300, stream=True)
            response.raise_for_status()
            with open(cached_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        ds = xr.open_dataset(cached_path, chunks='auto')
    else:
        nc_path = BASE_PATH / "Data" / "raster" / "CONUS_Climate_Data_1km.nc"
        ds = xr.open_dataset(nc_path, chunks='auto')
    
    return ds

def get_netcdf_variables():
    """Get list of available NetCDF variables grouped by type"""
    ds = load_netcdf()
    variables = list(ds.data_vars)
    ds.close()
    
    # Group variables by type
    grouped = {
        'LST_Day': [v for v in variables if v.startswith('LST_Day')],
        'LST_Night': [v for v in variables if v.startswith('LST_Night')],
        'LCZ': [v for v in variables if v.startswith('LCZ')],
        'NDVI': [v for v in variables if v.startswith('NDVI')],
        'Precip': [v for v in variables if v.startswith('Precip')],
        'ET': [v for v in variables if v.startswith('ET')],
        'Humidity': [v for v in variables if 'Humid' in v or 'humidity' in v.lower()]
    }
    return grouped

def get_cities_list():
    """Get unique list of cities"""
    df = load_analysis_data()
    return sorted(df['City'].unique().tolist())

def get_regions_list():
    """Get unique list of regions"""
    df = load_analysis_data()
    return sorted(df['Region'].unique().tolist())

def filter_data(df, city=None, region=None, year=None, season=None, time=None, lcz_class=None):
    """Filter analysis data by various criteria"""
    filtered = df.copy()
    
    if city:
        if isinstance(city, list):
            filtered = filtered[filtered['City'].isin(city)]
        else:
            filtered = filtered[filtered['City'] == city]
    
    if region:
        if isinstance(region, list):
            filtered = filtered[filtered['Region'].isin(region)]
        else:
            filtered = filtered[filtered['Region'] == region]
    
    if year:
        if isinstance(year, list):
            filtered = filtered[filtered['Year'].isin(year)]
        else:
            filtered = filtered[filtered['Year'] == year]
    
    if season:
        if isinstance(season, list):
            filtered = filtered[filtered['Season'].isin(season)]
        else:
            filtered = filtered[filtered['Season'] == season]
    
    if time:
        if isinstance(time, list):
            filtered = filtered[filtered['Time'].isin(time)]
        else:
            filtered = filtered[filtered['Time'] == time]
    
    if lcz_class:
        if isinstance(lcz_class, list):
            filtered = filtered[filtered['LCZ_Class'].isin(lcz_class)]
        else:
            filtered = filtered[filtered['LCZ_Class'] == lcz_class]
    
    return filtered

def get_city_info(city_name):
    """Get city information from shapefile"""
    gdf = load_city_boundaries()
    city_row = gdf[gdf['City'] == city_name]
    if len(city_row) == 0:
        return None
    return city_row.iloc[0]

def extract_raster_for_city(city_name, variable_name, buffer_km=20):
    """
    Extract raster data for a city with buffer.
    Returns clipped xarray DataArray and city boundary.
    """
    from shapely.ops import unary_union
    from shapely.geometry import box
    
    gdf = load_city_boundaries()
    city_geom = gdf[gdf['City'] == city_name].geometry.values[0]
    
    # Project to a meters-based CRS for buffering
    city_gdf = gdf[gdf['City'] == city_name].to_crs(epsg=5070)
    buffered = city_gdf.buffer(buffer_km * 1000)  # buffer in meters
    buffered_gdf = gpd.GeoDataFrame(geometry=buffered, crs=5070)
    buffered_gdf = buffered_gdf.to_crs(epsg=4326)
    
    # Get bounding box
    bounds = buffered_gdf.total_bounds  # minx, miny, maxx, maxy
    
    # Load and clip NetCDF
    ds = load_netcdf()
    
    if variable_name in ds.data_vars:
        da = ds[variable_name]
        
        # Clip to bounding box (assuming x, y are in projected coords)
        # We need to handle the coordinate system properly
        # For now, return the data array and bounds
        return da, bounds, city_geom, buffered_gdf.geometry.values[0]
    
    return None, None, None, None

# LCZ class definitions and colors
LCZ_CLASSES = {
    1: ("Compact high-rise", "#8c0000"),
    2: ("Compact mid-rise", "#d10000"),
    3: ("Compact low-rise", "#ff0000"),
    4: ("Open high-rise", "#bf4d00"),
    5: ("Open mid-rise", "#ff6600"),
    6: ("Open low-rise", "#ff9955"),
    7: ("Lightweight low-rise", "#faee05"),
    8: ("Large low-rise", "#bcbcbc"),
    9: ("Sparsely built", "#ffccaa"),
    10: ("Heavy industry", "#555555"),
    11: ("Dense trees", "#006a00"),
    12: ("Scattered trees", "#00aa00"),
    13: ("Bush, scrub", "#648c14"),
    14: ("Low plants", "#b9db79"),
    15: ("Bare rock/paved", "#000000"),
    16: ("Bare soil/sand", "#fbf7ae"),
    17: ("Water", "#6a6aff")
}

def get_lcz_color(lcz_class):
    """Get color for LCZ class"""
    return LCZ_CLASSES.get(int(lcz_class), ("Unknown", "#808080"))[1]

def get_lcz_name(lcz_class):
    """Get name for LCZ class"""
    return LCZ_CLASSES.get(int(lcz_class), ("Unknown", "#808080"))[0]
