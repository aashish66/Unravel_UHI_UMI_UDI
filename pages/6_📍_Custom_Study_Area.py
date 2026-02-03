"""
Custom Study Area - Explore any location in CONUS with file upload
"""
import streamlit as st
import sys
from pathlib import Path
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Polygon
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.raster_utils import (
    get_netcdf_dataset, extract_raster_for_geometry, create_lcz_colormap,
    LCZ_CMAP_COLORS, LCZ_NAMES, create_custom_area_figure,
    load_uploaded_geometry, parse_drawn_geometry
)

st.set_page_config(page_title="Custom Study Area", page_icon="📍", layout="wide")

st.title("📍 Custom Study Area")
st.markdown("Explore any area in CONUS - upload your own boundary or draw on the map!")

# Sidebar
st.sidebar.header("📋 Select Study Area Method")

method = st.sidebar.radio(
    "Choose input method:",
    options=["Draw on Map", "Upload File", "Manual Coordinates"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Options")
year = st.sidebar.selectbox("Year", options=[2000, 2005, 2010, 2015, 2020], index=4)
season = st.sidebar.selectbox("Season", options=['summer', 'winter', 'spring', 'fall'], index=0)

# Initialize geometry
study_geometry = None
study_gdf = None

# ========== METHOD 1: DRAW ON MAP ==========
if method == "Draw on Map":
    st.markdown("### 🗺️ Draw Your Study Area")
    st.markdown("Use the **rectangle** or **polygon** tool to draw your study area.")
    
    m = folium.Map(location=[39.0, -98.0], zoom_start=4, tiles='CartoDB positron')
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satellite'
    ).add_to(m)
    
    draw = Draw(
        draw_options={
            'polyline': False,
            'polygon': True,
            'circle': False,
            'marker': False,
            'circlemarker': False,
            'rectangle': True,
        },
        edit_options={'edit': False}
    )
    draw.add_to(m)
    folium.LayerControl().add_to(m)
    
    map_data = st_folium(m, width=900, height=400, key="draw_map")
    
    study_geometry = parse_drawn_geometry(map_data)
    
    if study_geometry:
        st.success(f"✅ Area selected: {study_geometry.area:.4f} sq degrees")
        study_gdf = gpd.GeoDataFrame(geometry=[study_geometry], crs="EPSG:4326")

# ========== METHOD 2: UPLOAD FILE ==========
elif method == "Upload File":
    st.markdown("### 📁 Upload Your Study Area")
    st.markdown("""
    **Supported formats:**
    - GeoJSON (.geojson, .json)
    - Shapefile (as .zip containing .shp, .shx, .dbf, .prj)
    """)
    
    uploaded_file = st.file_uploader(
        "Upload boundary file",
        type=['geojson', 'json', 'zip', 'shp'],
        help="Upload a GeoJSON or zipped Shapefile"
    )
    
    if uploaded_file:
        study_gdf = load_uploaded_geometry(uploaded_file)
        
        if study_gdf is not None and len(study_gdf) > 0:
            st.success(f"✅ Loaded {len(study_gdf)} feature(s)")
            
            # Show preview map
            study_geometry = study_gdf.unary_union
            centroid = study_geometry.centroid
            
            m = folium.Map(location=[centroid.y, centroid.x], zoom_start=8, tiles='CartoDB positron')
            folium.GeoJson(study_gdf, style_function=lambda x: {
                'fillColor': 'magenta', 'color': 'magenta', 'weight': 3, 'fillOpacity': 0.2
            }).add_to(m)
            st_folium(m, width=700, height=300, key="preview_map")

# ========== METHOD 3: MANUAL COORDINATES ==========
elif method == "Manual Coordinates":
    st.markdown("### 📍 Enter Coordinates")
    
    col1, col2 = st.columns(2)
    with col1:
        lat_min = st.number_input("Min Latitude", value=33.5, min_value=24.0, max_value=50.0, step=0.1)
        lon_min = st.number_input("Min Longitude", value=-112.5, min_value=-125.0, max_value=-66.0, step=0.1)
    with col2:
        lat_max = st.number_input("Max Latitude", value=34.0, min_value=24.0, max_value=50.0, step=0.1)
        lon_max = st.number_input("Max Longitude", value=-111.5, min_value=-125.0, max_value=-66.0, step=0.1)
    
    study_geometry = box(lon_min, lat_min, lon_max, lat_max)
    study_gdf = gpd.GeoDataFrame(geometry=[study_geometry], crs="EPSG:4326")
    
    st.info(f"📍 Bounding box: ({lat_min:.2f}, {lon_min:.2f}) to ({lat_max:.2f}, {lon_max:.2f})")

# ========== ANALYSIS SECTION ==========
if study_geometry is not None:
    st.markdown("---")
    st.markdown("## 🛰️ Raster Analysis")
    st.info("**Magenta line** = Study Area Boundary")
    
    analyze_button = st.button("🔍 Analyze Area", type="primary")
    
    if analyze_button:
        try:
            @st.cache_resource
            def load_netcdf():
                return get_netcdf_dataset()
            
            ds = load_netcdf()
            
            # LCZ Evolution
            st.markdown(f"### 🏘️ LCZ Classification (2000-2020)")
            
            lcz_cols = st.columns(5)
            years_list = [2000, 2005, 2010, 2015, 2020]
            
            for i, yr in enumerate(years_list):
                with lcz_cols[i]:
                    var_name = f'LCZ_{yr}'
                    if var_name in ds.data_vars:
                        data, pixel_bounds, geom = extract_raster_for_geometry(
                            ds, var_name, study_geometry, buffer_km=5
                        )
                        
                        if data is not None and data.size > 0:
                            cmap, norm = create_lcz_colormap()
                            fig = create_custom_area_figure(
                                data, study_geometry, pixel_bounds,
                                cmap=cmap, norm=norm, discrete=True,
                                title=f'LCZ {yr}', colorbar_shrink=0.4,
                                figsize=(4, 4)
                            )
                            st.pyplot(fig, use_container_width=True)
                            plt.close(fig)
                        else:
                            st.info("N/A")
                    else:
                        st.info("N/A")
            
            # SUHI Anomaly Maps - Day and Night
            st.markdown("---")
            st.markdown(f"### 🌡️ SUHI Anomaly Maps ({season.capitalize()} {year})")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**☀️ Daytime SUHI**")
                var_name = f'LST_Day_{season}_{year}'
                if var_name not in ds.data_vars:
                    var_name = f'LST_Day_mean_{year}'
                
                if var_name in ds.data_vars:
                    data, pixel_bounds, geom = extract_raster_for_geometry(
                        ds, var_name, study_geometry, buffer_km=5
                    )
                    
                    if data is not None and data.size > 0:
                        mean_val = np.nanmean(data)
                        anomaly = data - mean_val
                        vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 12)
                        
                        fig = create_custom_area_figure(
                            anomaly, study_geometry, pixel_bounds,
                            cmap='RdBu_r', title=f'Day SUHI Anomaly',
                            colorbar_label='Temp (°C)', vmin=-vmax, vmax=vmax,
                            colorbar_shrink=0.5, figsize=(5, 5)
                        )
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                        st.metric("Mean LST", f"{mean_val:.1f}°C")
                else:
                    st.info("Day LST N/A")
            
            with col2:
                st.markdown("**🌙 Nighttime SUHI**")
                var_name = f'LST_Night_{season}_{year}'
                if var_name not in ds.data_vars:
                    var_name = f'LST_Night_mean_{year}'
                
                if var_name in ds.data_vars:
                    data, pixel_bounds, geom = extract_raster_for_geometry(
                        ds, var_name, study_geometry, buffer_km=5
                    )
                    
                    if data is not None and data.size > 0:
                        mean_val = np.nanmean(data)
                        anomaly = data - mean_val
                        vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 12)
                        
                        fig = create_custom_area_figure(
                            anomaly, study_geometry, pixel_bounds,
                            cmap='RdBu_r', title=f'Night SUHI Anomaly',
                            colorbar_label='Temp (°C)', vmin=-vmax, vmax=vmax,
                            colorbar_shrink=0.5, figsize=(5, 5)
                        )
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                        st.metric("Mean LST", f"{mean_val:.1f}°C")
                else:
                    st.info("Night LST N/A")
            
            # UMI/UDI Anomaly Maps
            st.markdown("---")
            st.markdown(f"### 💧 UMI/UDI Anomaly Maps ({season.capitalize()} {year})")
            
            # Check for humidity variables
            humidity_vars = [v for v in ds.data_vars if 'humid' in v.lower() or 'Humid' in v]
            
            if humidity_vars:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**☀️ Daytime UMI**")
                    for pattern in humidity_vars:
                        if 'Day' in pattern or 'day' in pattern:
                            data, pixel_bounds, geom = extract_raster_for_geometry(
                                ds, pattern, study_geometry, buffer_km=5
                            )
                            if data is not None and data.size > 0:
                                mean_val = np.nanmean(data)
                                anomaly = data - mean_val
                                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 3)
                                
                                fig = create_custom_area_figure(
                                    anomaly, study_geometry, pixel_bounds,
                                    cmap='BrBG', title=f'Day UMI Anomaly',
                                    colorbar_label='Humidity', vmin=-vmax, vmax=vmax,
                                    colorbar_shrink=0.5, figsize=(5, 5)
                                )
                                st.pyplot(fig, use_container_width=True)
                                plt.close(fig)
                                break
                    else:
                        st.info("Day humidity N/A")
                
                with col2:
                    st.markdown("**🌙 Nighttime UMI (UDI = -UMI)**")
                    for pattern in humidity_vars:
                        if 'Night' in pattern or 'night' in pattern:
                            data, pixel_bounds, geom = extract_raster_for_geometry(
                                ds, pattern, study_geometry, buffer_km=5
                            )
                            if data is not None and data.size > 0:
                                mean_val = np.nanmean(data)
                                anomaly = data - mean_val
                                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 3)
                                
                                fig = create_custom_area_figure(
                                    anomaly, study_geometry, pixel_bounds,
                                    cmap='BrBG', title=f'Night UMI Anomaly',
                                    colorbar_label='Humidity', vmin=-vmax, vmax=vmax,
                                    colorbar_shrink=0.5, figsize=(5, 5)
                                )
                                st.pyplot(fig, use_container_width=True)
                                plt.close(fig)
                                break
                    else:
                        st.info("Night humidity N/A")
            else:
                st.info("💧 Humidity raster data not available in NetCDF.")
            
            # NDVI
            st.markdown("---")
            st.markdown(f"### 🌿 NDVI Vegetation Index ({year})")
            
            var_name = f'NDVI_mean_{year}'
            if var_name in ds.data_vars:
                data, pixel_bounds, geom = extract_raster_for_geometry(
                    ds, var_name, study_geometry, buffer_km=5
                )
                
                if data is not None and data.size > 0:
                    fig = create_custom_area_figure(
                        data, study_geometry, pixel_bounds,
                        cmap='RdYlGn', title=f'NDVI {year}',
                        colorbar_label='NDVI', vmin=0, vmax=1,
                        colorbar_shrink=0.5, figsize=(6, 5)
                    )
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                    st.metric("Mean NDVI", f"{np.nanmean(data):.3f}")
            else:
                st.info("NDVI N/A")
            
            # LCZ Statistics
            st.markdown("---")
            st.markdown("### 📊 LCZ Composition")
            
            lcz_var = f'LCZ_{year}'
            if lcz_var in ds.data_vars:
                data, pixel_bounds, geom = extract_raster_for_geometry(
                    ds, lcz_var, study_geometry, buffer_km=5
                )
                
                if data is not None and data.size > 0:
                    unique, counts = np.unique(data[~np.isnan(data)].astype(int), return_counts=True)
                    total = counts.sum()
                    
                    lcz_stats = []
                    for lcz, count in zip(unique, counts):
                        if 1 <= lcz <= 17:
                            lcz_stats.append({
                                'LCZ': int(lcz),
                                'Name': LCZ_NAMES.get(int(lcz), 'Unknown'),
                                'Pixels': int(count),
                                'Percentage': f"{100*count/total:.1f}%"
                            })
                    
                    if lcz_stats:
                        stats_df = pd.DataFrame(lcz_stats).sort_values('Pixels', ascending=False)
                        st.dataframe(stats_df, use_container_width=True, hide_index=True)
                        
                        urban_pct = sum([s['Pixels'] for s in lcz_stats if s['LCZ'] <= 10]) / total * 100
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Urban (LCZ 1-10)", f"{urban_pct:.1f}%")
                        with col2:
                            st.metric("Rural (LCZ 11-17)", f"{100-urban_pct:.1f}%")
        
        except Exception as e:
            st.error(f"Error analyzing area: {e}")
            st.exception(e)
else:
    st.info("👆 Select a study area using one of the methods in the sidebar, then click **Analyze Area**.")

# LCZ Legend
st.markdown("---")
with st.expander("📋 LCZ Class Legend"):
    lcz_cols = st.columns(6)
    for i, lcz_num in enumerate(range(1, 18)):
        lcz_name = LCZ_NAMES.get(lcz_num, "Unknown")
        lcz_color = LCZ_CMAP_COLORS.get(lcz_num, "#808080")
        with lcz_cols[i % 6]:
            st.markdown(
                f'<div style="background-color:{lcz_color}; padding:4px; border-radius:4px; margin:1px;">'
                f'<span style="color:{"white" if lcz_num <= 10 else "black"}; font-size:11px;"><b>LCZ {lcz_num}</b></span><br>'
                f'<small style="color:{"white" if lcz_num <= 10 else "black"};">{lcz_name}</small></div>',
                unsafe_allow_html=True
            )
