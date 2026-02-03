"""
City Explorer - Deep-dive into individual cities with raster visualization
"""
import streamlit as st
import sys
from pathlib import Path
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import (
    load_analysis_data, load_city_boundaries, get_cities_list, 
    get_regions_list, filter_data, get_lcz_name, get_lcz_color, LCZ_CLASSES
)
from utils.map_utils import create_city_detail_map
from utils.chart_utils import (
    create_temporal_trend, create_seasonal_heatmap, create_lcz_bar_chart,
    create_metrics_cards_data, create_scatter_coupling
)
from utils.raster_utils import (
    get_netcdf_dataset, extract_raster_for_geometry, extract_raster_for_city,
    create_lcz_colormap, display_figure_in_streamlit, LCZ_CMAP_COLORS, LCZ_NAMES,
    create_raster_figure_with_boundary
)

st.set_page_config(page_title="City Explorer", page_icon="🏙️", layout="wide")

st.title("🏙️ City Explorer")
st.markdown("Deep-dive into urban climate metrics with raster visualization")

# Load data
@st.cache_data
def load_data():
    df = load_analysis_data()
    gdf = load_city_boundaries()
    return df, gdf

df, cities_gdf = load_data()

# Sidebar - City Selection
st.sidebar.header("🔧 Select City")

regions = get_regions_list()
region = st.sidebar.selectbox("Region", options=['All'] + regions)

if region != 'All':
    available_cities = df[df['Region'] == region]['City'].unique().tolist()
else:
    available_cities = get_cities_list()

city = st.sidebar.selectbox("City", options=sorted(available_cities))

city_gdf = cities_gdf[cities_gdf['City'] == city]
city_info = city_gdf.iloc[0] if len(city_gdf) > 0 else None

st.sidebar.markdown("---")
st.sidebar.header("🎛️ Raster Options")
year = st.sidebar.selectbox("Focus Year", options=[2000, 2005, 2010, 2015, 2020], index=4)
season = st.sidebar.selectbox("Season", options=['summer', 'winter', 'spring', 'fall'], index=0)

city_data = filter_data(df, city=city)
city_year_data = filter_data(df, city=city, year=year)

# Create buffer for overlays
if len(city_gdf) > 0:
    city_proj = city_gdf.to_crs(epsg=5070)
    buffer_proj = city_proj.buffer(20000)
    buffer_gdf = gpd.GeoDataFrame(geometry=buffer_proj, crs=5070).to_crs(epsg=4326)
else:
    buffer_gdf = None

# Header with city info
col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

with col1:
    st.markdown(f"## {city}, {city_info['State'] if city_info is not None else ''}")
    region_name = city_data['Region'].iloc[0] if len(city_data) > 0 else 'Unknown'
    st.markdown(f"**Region:** {region_name}")

with col2:
    if city_info is not None and 'Census2020' in city_info.index:
        pop = city_info['Census2020']
        if pd.notna(pop):
            st.metric("Population (2020)", f"{int(pop):,}")

with col3:
    if city_info is not None and 'Census2010' in city_info.index:
        pop = city_info['Census2010']
        if pd.notna(pop):
            st.metric("Population (2010)", f"{int(pop):,}")

with col4:
    if city_info is not None:
        for col in ['MHHIncome2', 'MHHIncom_1']:
            if col in city_info.index and pd.notna(city_info[col]):
                st.metric("Median Income", f"${int(city_info[col]):,}")
                break

# Metrics cards - Day AND Night
st.markdown("---")
st.markdown(f"### 📊 Climate Metrics ({year}, {season.capitalize()})")

metrics = create_metrics_cards_data(city_data)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("☀️ SUHI Day", f"{metrics['suhi_day']:.1f}°C")
with col2:
    st.metric("🌙 SUHI Night", f"{metrics['suhi_night']:.1f}°C")
with col3:
    st.metric("☀️ UMI Day", f"{metrics['umi_day']:.1f} g/kg")
with col4:
    st.metric("🌙 UMI Night", f"{metrics['umi_night']:.1f} g/kg")
with col5:
    st.metric("☀️ UDI Day", f"{metrics['udi_day']:.1f} g/kg")
with col6:
    st.metric("🌙 UDI Night", f"{metrics['udi_night']:.1f} g/kg")

# Interactive Map and Trend
st.markdown("---")
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 🗺️ City Boundary with 20km Buffer")
    
    if len(city_gdf) > 0:
        centroid = city_gdf.geometry.centroid.iloc[0]
        bounds = buffer_gdf.total_bounds
        
        m = folium.Map(location=[centroid.y, centroid.x], zoom_start=9, tiles='CartoDB positron')
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satellite'
        ).add_to(m)
        
        folium.GeoJson(buffer_gdf, name='20km Buffer Zone',
            style_function=lambda x: {'fillColor': '#e8f4f8', 'color': '#3498db', 
                                       'weight': 2, 'dashArray': '5, 5', 'fillOpacity': 0.2}
        ).add_to(m)
        
        folium.GeoJson(city_gdf, name='Urban Boundary',
            style_function=lambda x: {'fillColor': '#e74c3c', 'color': '#c0392b', 
                                       'weight': 4, 'fillOpacity': 0.3}
        ).add_to(m)
        
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
        folium.LayerControl().add_to(m)
        st_folium(m, width=500, height=400, key="city_map")
    else:
        st.warning("City boundary not found")

with col2:
    st.markdown("### 📈 20-Year SUHI Trend")
    summer_day = filter_data(city_data, season='summer', time='Day')
    fig = create_temporal_trend(summer_day, metric='SUHI', group_by='LCZ_Class',
                                title=f'{city} - Summer Daytime SUHI by LCZ (2000-2020)')
    st.plotly_chart(fig, use_container_width=True, key="trend_chart")

# ========== RASTER VISUALIZATION SECTION ==========
st.markdown("---")
st.markdown("## 🛰️ Raster Visualization (20km Buffer Area)")
st.info("Red solid line = Urban Boundary | Blue dashed line = 20km Buffer")

@st.cache_resource
def load_netcdf():
    return get_netcdf_dataset()

try:
    ds = load_netcdf()
    
    # LCZ Evolution Row
    st.markdown("### 🏘️ LCZ Classification Evolution (2000-2020)")
    
    lcz_cols = st.columns(5)
    years = [2000, 2005, 2010, 2015, 2020]
    
    for i, yr in enumerate(years):
        with lcz_cols[i]:
            var_name = f'LCZ_{yr}'
            if var_name in ds.data_vars:
                data, pixel_bounds, _ = extract_raster_for_city(ds, var_name, city_gdf, buffer_km=20)
                
                if data is not None:
                    cmap, norm = create_lcz_colormap()
                    fig = create_raster_figure_with_boundary(
                        data, city_gdf, buffer_gdf, pixel_bounds,
                        cmap=cmap, norm=norm, discrete=True,
                        title=f'LCZ {yr}', colorbar_label=None,
                        show_buffer=False
                    )
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                else:
                    st.info(f"LCZ {yr} N/A")
            else:
                st.info(f"LCZ {yr} not found")

    # SUHI Anomaly Maps - Day vs Night
    st.markdown("---")
    st.markdown(f"### 🌡️ SUHI Anomaly Maps ({season.capitalize()} {year})")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**☀️ Daytime SUHI**")
        var_name = f'LST_Day_{season}_{year}'
        if var_name not in ds.data_vars:
            var_name = f'LST_Day_mean_{year}'
        
        if var_name in ds.data_vars:
            data, pixel_bounds, _ = extract_raster_for_city(ds, var_name, city_gdf, buffer_km=20)
            if data is not None:
                mean_val = np.nanmean(data)
                anomaly = data - mean_val
                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 10)
                
                fig = create_raster_figure_with_boundary(
                    anomaly, city_gdf, buffer_gdf, pixel_bounds,
                    cmap='RdBu_r', title=f'SUHI Day - {season.capitalize()} {year}',
                    colorbar_label='Temp (°C)', vmin=-vmax, vmax=vmax, colorbar_shrink=0.5,
                    show_buffer=False
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
        else:
            st.info("Day LST data not available")
    
    with col2:
        st.markdown("**🌙 Nighttime SUHI**")
        var_name = f'LST_Night_{season}_{year}'
        if var_name not in ds.data_vars:
            var_name = f'LST_Night_mean_{year}'
        
        if var_name in ds.data_vars:
            data, pixel_bounds, _ = extract_raster_for_city(ds, var_name, city_gdf, buffer_km=20)
            if data is not None:
                mean_val = np.nanmean(data)
                anomaly = data - mean_val
                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 10)
                
                fig = create_raster_figure_with_boundary(
                    anomaly, city_gdf, buffer_gdf, pixel_bounds,
                    cmap='RdBu_r', title=f'SUHI Night - {season.capitalize()} {year}',
                    colorbar_label='Temp (°C)', vmin=-vmax, vmax=vmax, colorbar_shrink=0.5,
                    show_buffer=False
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
        else:
            st.info("Night LST data not available")

    # UMI Anomaly Maps - Day vs Night (NEW!)
    st.markdown("---")
    st.markdown(f"### 💧 UMI/UDI Anomaly Maps ({season.capitalize()} {year})")
    
    # Check for humidity variables
    humidity_vars = [v for v in ds.data_vars if 'humid' in v.lower() or 'Humid' in v]
    
    if humidity_vars:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**☀️ Daytime UMI**")
            # Try to find appropriate humidity variable
            for pattern in [f'Humidity_Day_{season}_{year}', f'Humidity_Day_mean_{year}', 
                           f'humidity_day_{year}', humidity_vars[0] if humidity_vars else None]:
                if pattern and pattern in ds.data_vars:
                    data, pixel_bounds, _ = extract_raster_for_city(ds, pattern, city_gdf, buffer_km=20)
                    if data is not None:
                        mean_val = np.nanmean(data)
                        anomaly = data - mean_val
                        vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 5)
                        
                        fig = create_raster_figure_with_boundary(
                            anomaly, city_gdf, buffer_gdf, pixel_bounds,
                            cmap='BrBG', title=f'UMI Day - {season.capitalize()} {year}',
                            colorbar_label='Humidity', vmin=-vmax, vmax=vmax, colorbar_shrink=0.5,
                            show_buffer=False
                        )
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                        break
            else:
                st.info("Day humidity data not available")
        
        with col2:
            st.markdown("**🌙 Nighttime UMI**")
            for pattern in [f'Humidity_Night_{season}_{year}', f'Humidity_Night_mean_{year}',
                           f'humidity_night_{year}']:
                if pattern in ds.data_vars:
                    data, pixel_bounds, _ = extract_raster_for_city(ds, pattern, city_gdf, buffer_km=20)
                    if data is not None:
                        mean_val = np.nanmean(data)
                        anomaly = data - mean_val
                        vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 5)
                        
                        fig = create_raster_figure_with_boundary(
                            anomaly, city_gdf, buffer_gdf, pixel_bounds,
                            cmap='BrBG', title=f'UMI Night - {season.capitalize()} {year}',
                            colorbar_label='Humidity', vmin=-vmax, vmax=vmax, colorbar_shrink=0.5,
                            show_buffer=False
                        )
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                        break
            else:
                st.info("Night humidity data not available")
    else:
        st.info("Humidity raster data not available in NetCDF. UMI values from analysis CSV are shown in charts below.")

except Exception as e:
    st.error(f"Error loading raster data: {e}")

# ========== END RASTER SECTION ==========

# Seasonal patterns
st.markdown("---")
st.markdown("### 🌡️ Seasonal Patterns")

col1, col2 = st.columns(2)

with col1:
    fig = create_seasonal_heatmap(city_data, metric='SUHI', title=f'{city} - SUHI Seasonal Pattern')
    st.plotly_chart(fig, use_container_width=True, key="suhi_heatmap")

with col2:
    fig = create_seasonal_heatmap(city_data, metric='UMI', title=f'{city} - UMI Seasonal Pattern')
    st.plotly_chart(fig, use_container_width=True, key="umi_heatmap")

# LCZ Analysis
st.markdown("---")
st.markdown(f"### 🏘️ Climate by Local Climate Zone ({year})")

col1, col2 = st.columns(2)

with col1:
    fig = create_lcz_bar_chart(city_year_data, metric='SUHI', show_day_night=True,
                               title=f'{city} - SUHI by LCZ Class ({year})')
    st.plotly_chart(fig, use_container_width=True, key="lcz_suhi")

with col2:
    fig = create_lcz_bar_chart(city_year_data, metric='UMI', show_day_night=True,
                               title=f'{city} - UMI by LCZ Class ({year})')
    st.plotly_chart(fig, use_container_width=True, key="lcz_umi")

# Heat-Moisture Coupling
st.markdown("---")
st.markdown("### 🔥💧 Heat-Moisture Coupling")

summer_data = filter_data(city_data, season='summer')
fig = create_scatter_coupling(summer_data, title=f'{city} - SUHI vs UMI Coupling (Summer, All Years)')
st.plotly_chart(fig, use_container_width=True, key="coupling")

# LCZ Legend
st.markdown("---")
with st.expander("📋 LCZ Class Legend (Standard Colors)"):
    lcz_cols = st.columns(6)
    for i, lcz_num in enumerate(range(1, 18)):
        lcz_name = LCZ_NAMES.get(lcz_num, "Unknown")
        lcz_color = LCZ_CMAP_COLORS.get(lcz_num, "#808080")
        with lcz_cols[i % 6]:
            st.markdown(
                f'<div style="background-color:{lcz_color}; padding:5px; border-radius:5px; margin:2px;">'
                f'<span style="color:{"white" if lcz_num <= 10 else "black"}; font-weight:bold;">LCZ {lcz_num}</span><br>'
                f'<small style="color:{"white" if lcz_num <= 10 else "black"};">{lcz_name}</small></div>',
                unsafe_allow_html=True
            )

# Data table
st.markdown("---")
with st.expander("📊 View Raw Data"):
    st.dataframe(city_data.round(2), use_container_width=True)
    csv = city_data.to_csv(index=False)
    st.download_button(label="📥 Download CSV", data=csv, 
                       file_name=f"{city}_climate_data.csv", mime="text/csv")
