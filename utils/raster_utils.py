"""
Raster utilities for extracting and visualizing NetCDF data
"""
import numpy as np
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from shapely.geometry import box, Polygon, mapping
from shapely.ops import unary_union
from io import BytesIO
import base64
from pathlib import Path
import streamlit as st
import json
import tempfile
import zipfile
import os

# Standard LCZ colors
LCZ_CMAP_COLORS = {
    1:  "#8E0000", 2:  "#D30000", 3:  "#FF0000", 4:  "#8E4B00",
    5:  "#D36F00", 6:  "#FF8E00", 7:  "#FFCC00", 8:  "#FFE680",
    9:  "#FFEBB3", 10: "#999999", 11: "#006A00", 12: "#00A000",
    13: "#78D000", 14: "#CCFF66", 15: "#A0A0A0", 16: "#E6CBA8",
    17: "#4A97C9",
}

LCZ_NAMES = {
    1: 'Compact high-rise', 2: 'Compact mid-rise', 3: 'Compact low-rise',
    4: 'Open high-rise', 5: 'Open mid-rise', 6: 'Open low-rise',
    7: 'Lightweight low-rise', 8: 'Large low-rise', 9: 'Sparsely built',
    10: 'Heavy industry', 11: 'Dense trees', 12: 'Scattered trees',
    13: 'Bush/scrub', 14: 'Low plants', 15: 'Bare rock',
    16: 'Bare soil', 17: 'Water'
}

# CONUS grid parameters
CONUS_LON_MIN, CONUS_LON_MAX = -125, -66
CONUS_LAT_MIN, CONUS_LAT_MAX = 24, 50
GRID_WIDTH, GRID_HEIGHT = 6435, 2767


def create_lcz_colormap():
    """Create a discrete colormap for LCZ classes"""
    colors = ['#ffffff']
    for i in range(1, 18):
        colors.append(LCZ_CMAP_COLORS.get(i, '#ffffff'))
    cmap = mcolors.ListedColormap(colors)
    bounds = np.arange(-0.5, 18.5, 1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    return cmap, norm


@st.cache_resource
def get_netcdf_dataset():
    """Get the NetCDF dataset (cached) - uses S3 loading from data_loader"""
    from utils.data_loader import load_netcdf
    return load_netcdf()


def lonlat_to_pixel(lon, lat):
    """Convert lon/lat to pixel coordinates"""
    px = (lon - CONUS_LON_MIN) / (CONUS_LON_MAX - CONUS_LON_MIN) * GRID_WIDTH
    py = (CONUS_LAT_MAX - lat) / (CONUS_LAT_MAX - CONUS_LAT_MIN) * GRID_HEIGHT
    return px, py


def pixel_to_lonlat(px, py):
    """Convert pixel coordinates to lon/lat"""
    lon = CONUS_LON_MIN + px / GRID_WIDTH * (CONUS_LON_MAX - CONUS_LON_MIN)
    lat = CONUS_LAT_MAX - py / GRID_HEIGHT * (CONUS_LAT_MAX - CONUS_LAT_MIN)
    return lon, lat


def geometry_to_pixel_coords(geometry, x_offset, y_offset):
    """Convert geometry to pixel coordinates relative to extracted raster"""
    if hasattr(geometry, 'exterior'):
        coords = list(geometry.exterior.coords)
    elif hasattr(geometry, 'coords'):
        coords = list(geometry.coords)
    else:
        return []
    
    pixel_coords = []
    for lon, lat in coords:
        px, py = lonlat_to_pixel(lon, lat)
        pixel_coords.append((px - x_offset, py - y_offset))
    return pixel_coords


def extract_raster_for_geometry(ds, variable_name, geometry, buffer_km=20):
    """
    Extract raster data clipped to geometry with buffer.
    Returns data, pixel bounds, and geometry pixel coords for overlay.
    """
    # Get geometry in WGS84
    if hasattr(geometry, 'geometry'):
        geom = geometry.geometry.iloc[0] if hasattr(geometry.geometry, 'iloc') else geometry.geometry
    else:
        geom = geometry
    
    # Get bounds
    bounds = geom.bounds  # minx, miny, maxx, maxy
    
    # Add buffer in degrees (approximate: 1 degree ~ 111km)
    buffer_deg = buffer_km / 111.0
    lon_min = bounds[0] - buffer_deg
    lon_max = bounds[2] + buffer_deg
    lat_min = bounds[1] - buffer_deg
    lat_max = bounds[3] + buffer_deg
    
    # Convert to pixels
    x_min, y_max_pix = lonlat_to_pixel(lon_min, lat_max)
    x_max, y_min_pix = lonlat_to_pixel(lon_max, lat_min)
    
    # Clamp to grid
    x_min = int(max(0, min(x_min, GRID_WIDTH - 1)))
    x_max = int(max(0, min(x_max, GRID_WIDTH - 1)))
    y_min = int(max(0, min(y_max_pix, GRID_HEIGHT - 1)))
    y_max = int(max(0, min(y_min_pix, GRID_HEIGHT - 1)))
    
    if x_max <= x_min or y_max <= y_min:
        return None, None, None
    
    # Extract data
    if variable_name in ds.data_vars:
        data = ds[variable_name].isel(
            x=slice(x_min, x_max),
            y=slice(y_min, y_max)
        ).values
        return data, (x_min, x_max, y_min, y_max), geom
    
    return None, None, None


def extract_raster_for_city(ds, variable_name, city_gdf, buffer_km=20):
    """Extract raster data for a city with buffer"""
    geom = city_gdf.geometry.iloc[0]
    return extract_raster_for_geometry(ds, variable_name, geom, buffer_km)


def extract_raster_for_bounds(ds, variable_name, lon_min, lon_max, lat_min, lat_max):
    """Extract raster data for bounding box"""
    geom = box(lon_min, lat_min, lon_max, lat_max)
    return extract_raster_for_geometry(ds, variable_name, geom, buffer_km=0)


def create_raster_figure_with_boundary(data, city_gdf, buffer_gdf, pixel_bounds,
                                       cmap, title, colorbar_label=None,
                                       vmin=None, vmax=None, discrete=False, norm=None,
                                       figsize=(5, 5), colorbar_shrink=0.5, show_buffer=True):
    """
    Create raster figure with city and buffer boundary overlays.
    Colorbar is shrunk to 50% of figure height.
    
    Args:
        show_buffer: If False, only show urban boundary (no buffer line)
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    if discrete and norm is not None:
        im = ax.imshow(data, cmap=cmap, norm=norm, interpolation='nearest')
    else:
        im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
    
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.axis('off')
    
    x_min, x_max, y_min, y_max = pixel_bounds
    
    # Add city boundary overlay
    if city_gdf is not None:
        city_geom = city_gdf.geometry.iloc[0]
        city_coords = geometry_to_pixel_coords(city_geom, x_min, y_min)
        if city_coords:
            xs = [c[0] for c in city_coords]
            ys = [c[1] for c in city_coords]
            ax.plot(xs, ys, color='red', linewidth=2, linestyle='-')
    
    # Add buffer boundary overlay (only if show_buffer is True)
    if show_buffer and buffer_gdf is not None:
        buffer_geom = buffer_gdf.geometry.iloc[0]
        buffer_coords = geometry_to_pixel_coords(buffer_geom, x_min, y_min)
        if buffer_coords:
            xs = [c[0] for c in buffer_coords]
            ys = [c[1] for c in buffer_coords]
            ax.plot(xs, ys, color='blue', linewidth=1.5, linestyle='--')
    
    # Add colorbar (shrunk to 50%)
    if colorbar_label:
        cbar = plt.colorbar(im, ax=ax, shrink=colorbar_shrink, pad=0.02)
        cbar.set_label(colorbar_label, fontsize=8)
        cbar.ax.tick_params(labelsize=7)
    
    # Add legend (adjust based on show_buffer)
    if show_buffer:
        legend_elements = [
            Line2D([0], [0], color='red', linewidth=2, linestyle='-', label='Urban'),
            Line2D([0], [0], color='blue', linewidth=1.5, linestyle='--', label='Buffer')
        ]
    else:
        legend_elements = [
            Line2D([0], [0], color='red', linewidth=2, linestyle='-', label='Urban')
        ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=6, framealpha=0.8)
    
    plt.tight_layout()
    return fig


def create_custom_area_figure(data, geometry, pixel_bounds, cmap, title,
                              colorbar_label=None, vmin=None, vmax=None,
                              discrete=False, norm=None, figsize=(5, 5),
                              colorbar_shrink=0.5):
    """
    Create raster figure for custom area with boundary overlay.
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    if discrete and norm is not None:
        im = ax.imshow(data, cmap=cmap, norm=norm, interpolation='nearest')
    else:
        im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
    
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.axis('off')
    
    x_min, x_max, y_min, y_max = pixel_bounds
    
    # Add study area boundary
    if geometry is not None:
        coords = geometry_to_pixel_coords(geometry, x_min, y_min)
        if coords:
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            ax.plot(xs, ys, color='magenta', linewidth=2, linestyle='-')
            ax.fill(xs, ys, color='magenta', alpha=0.1)
    
    # Add colorbar (shrunk to 50%)
    if colorbar_label:
        cbar = plt.colorbar(im, ax=ax, shrink=colorbar_shrink, pad=0.02)
        cbar.set_label(colorbar_label, fontsize=8)
        cbar.ax.tick_params(labelsize=7)
    
    # Add legend
    legend_elements = [
        Line2D([0], [0], color='magenta', linewidth=2, linestyle='-', label='Study Area')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=6, framealpha=0.8)
    
    plt.tight_layout()
    return fig


def load_uploaded_geometry(uploaded_file):
    """
    Load geometry from uploaded GeoJSON or Shapefile (zipped).
    Returns GeoDataFrame.
    """
    if uploaded_file is None:
        return None
    
    filename = uploaded_file.name.lower()
    
    try:
        if filename.endswith('.geojson') or filename.endswith('.json'):
            # GeoJSON file
            content = uploaded_file.read().decode('utf-8')
            gdf = gpd.read_file(BytesIO(content.encode()))
            return gdf.to_crs(epsg=4326)
        
        elif filename.endswith('.zip'):
            # Zipped shapefile
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, 'uploaded.zip')
                with open(zip_path, 'wb') as f:
                    f.write(uploaded_file.read())
                
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(tmpdir)
                
                # Find .shp file
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                if shp_files:
                    shp_path = os.path.join(tmpdir, shp_files[0])
                    gdf = gpd.read_file(shp_path)
                    return gdf.to_crs(epsg=4326)
        
        elif filename.endswith('.shp'):
            # Single shapefile (may not work without supporting files)
            gdf = gpd.read_file(uploaded_file)
            return gdf.to_crs(epsg=4326)
    
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None
    
    return None


def parse_drawn_geometry(map_data):
    """
    Parse drawn geometry from Folium map data.
    Returns Shapely geometry or None.
    """
    if not map_data:
        return None
    
    # Check for last active drawing
    if 'last_active_drawing' in map_data and map_data['last_active_drawing']:
        drawing = map_data['last_active_drawing']
        if drawing and 'geometry' in drawing:
            geom_dict = drawing['geometry']
            if geom_dict['type'] == 'Polygon':
                coords = geom_dict['coordinates'][0]
                return Polygon([(c[0], c[1]) for c in coords])
    
    # Check for all drawings
    if 'all_drawings' in map_data and map_data['all_drawings']:
        for drawing in map_data['all_drawings']:
            if drawing and 'geometry' in drawing:
                geom_dict = drawing['geometry']
                if geom_dict['type'] == 'Polygon':
                    coords = geom_dict['coordinates'][0]
                    return Polygon([(c[0], c[1]) for c in coords])
    
    return None


def display_figure_in_streamlit(fig, caption=None):
    """Display a matplotlib figure in Streamlit"""
    if fig is not None:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        st.image(buf, caption=caption, use_container_width=True)
        plt.close(fig)
    else:
        st.warning(f"Data not available for {caption}")
