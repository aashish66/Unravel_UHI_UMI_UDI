"""
Day/Night Comparison - Compare daytime and nighttime urban climate patterns
"""
import streamlit as st
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import (
    load_analysis_data, load_city_boundaries, get_cities_list, 
    get_regions_list, filter_data, LCZ_CLASSES
)
from utils.chart_utils import create_lcz_bar_chart, LCZ_COLORS, REGION_COLORS
from utils.raster_utils import (
    get_netcdf_dataset, extract_raster_for_city, create_lcz_colormap,
    create_raster_figure_with_boundary
)

st.set_page_config(page_title="Day/Night Comparison", page_icon="🌓", layout="wide")

st.title("🌓 Day/Night Comparison")
st.markdown("Compare daytime and nighttime urban heat island patterns")

# Load data
@st.cache_data
def load_data():
    df = load_analysis_data()
    gdf = load_city_boundaries()
    return df, gdf

df, cities_gdf = load_data()

# Sidebar filters
st.sidebar.header("🔧 Filters")

# City selection
cities = get_cities_list()
city = st.sidebar.selectbox("Select City", options=cities, index=cities.index('New York') if 'New York' in cities else 0)

year = st.sidebar.selectbox("Year", options=[2000, 2005, 2010, 2015, 2020], index=4)
season = st.sidebar.selectbox("Season", options=['summer', 'winter', 'spring', 'fall', 'annual'], index=0)

# Get city data
city_gdf = cities_gdf[cities_gdf['City'] == city]
city_data = filter_data(df, city=city, year=year, season=season)
city_day = filter_data(df, city=city, year=year, season=season, time='Day')
city_night = filter_data(df, city=city, year=year, season=season, time='Night')

# Header
st.markdown(f"## {city} - {season.capitalize()} {year}")

# Summary metrics comparison
st.markdown("### 📊 Day vs Night Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🌡️ SUHI (Surface Urban Heat Island)")
    day_suhi = city_day['SUHI'].mean() if len(city_day) > 0 else 0
    night_suhi = city_night['SUHI'].mean() if len(city_night) > 0 else 0
    diff_suhi = day_suhi - night_suhi
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("☀️ Day", f"{day_suhi:.2f}°C")
    with subcol2:
        st.metric("🌙 Night", f"{night_suhi:.2f}°C", f"{-diff_suhi:+.2f}°C")

with col2:
    st.markdown("#### 💧 UMI (Urban Moisture Island)")
    day_umi = city_day['UMI'].mean() if len(city_day) > 0 else 0
    night_umi = city_night['UMI'].mean() if len(city_night) > 0 else 0
    diff_umi = day_umi - night_umi
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("☀️ Day", f"{day_umi:.2f} g/kg")
    with subcol2:
        st.metric("🌙 Night", f"{night_umi:.2f} g/kg", f"{-diff_umi:+.2f}")

with col3:
    st.markdown("#### 🏜️ UDI (Urban Dry Island)")
    day_udi = -day_umi
    night_udi = -night_umi
    diff_udi = day_udi - night_udi
    
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("☀️ Day", f"{day_udi:.2f} g/kg")
    with subcol2:
        st.metric("🌙 Night", f"{night_udi:.2f} g/kg", f"{-diff_udi:+.2f}")

# Raster comparison - Day vs Night
st.markdown("---")
st.markdown("### 🛰️ LST Anomaly Maps - Day vs Night")

try:
    @st.cache_resource
    def load_netcdf():
        return get_netcdf_dataset()
    
    ds = load_netcdf()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**☀️ Daytime LST Anomaly**")
        var_name = f'LST_Day_{season}_{year}'
        if var_name not in ds.data_vars:
            var_name = f'LST_Day_mean_{year}'
        
        if var_name in ds.data_vars:
            data, pixel_bounds, geom = extract_raster_for_city(ds, var_name, city_gdf, buffer_km=20)
            
            if data is not None:
                mean_val = np.nanmean(data)
                anomaly = data - mean_val
                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 12)
                
                # Create buffer GeoDataFrame for the function
                buffer_gdf = city_gdf.copy()
                buffer_gdf.geometry = buffer_gdf.geometry.buffer(20 / 111.0)
                
                fig = create_raster_figure_with_boundary(
                    anomaly, city_gdf, buffer_gdf, pixel_bounds,
                    cmap='RdBu_r', title=f'Daytime LST Anomaly\n{season.capitalize()} {year}',
                    colorbar_label='Temperature Anomaly (°C)', vmin=-vmax, vmax=vmax,
                    figsize=(6, 6), colorbar_shrink=0.8, show_buffer=False
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            else:
                st.info("Day LST data not available for this city")
        else:
            st.info(f"Variable {var_name} not found")
    
    with col2:
        st.markdown("**🌙 Nighttime LST Anomaly**")
        var_name = f'LST_Night_{season}_{year}'
        if var_name not in ds.data_vars:
            var_name = f'LST_Night_mean_{year}'
        
        if var_name in ds.data_vars:
            data, pixel_bounds, geom = extract_raster_for_city(ds, var_name, city_gdf, buffer_km=20)
            
            if data is not None:
                mean_val = np.nanmean(data)
                anomaly = data - mean_val
                vmax = min(max(abs(np.nanmin(anomaly)), abs(np.nanmax(anomaly))), 12)
                
                # Create buffer GeoDataFrame for the function
                buffer_gdf = city_gdf.copy()
                buffer_gdf.geometry = buffer_gdf.geometry.buffer(20 / 111.0)
                
                fig = create_raster_figure_with_boundary(
                    anomaly, city_gdf, buffer_gdf, pixel_bounds,
                    cmap='RdBu_r', title=f'Nighttime LST Anomaly\n{season.capitalize()} {year}',
                    colorbar_label='Temperature Anomaly (°C)', vmin=-vmax, vmax=vmax,
                    figsize=(6, 6), colorbar_shrink=0.8, show_buffer=False
                )
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            else:
                st.info("Night LST data not available for this city")
        else:
            st.info(f"Variable {var_name} not found")

except Exception as e:
    st.error(f"Error loading raster data: {e}")

# LCZ comparison - Day vs Night
st.markdown("---")
st.markdown("### 🏘️ SUHI by LCZ Class - Day vs Night")

# Create side-by-side bar charts
col1, col2 = st.columns(2)

with col1:
    if len(city_day) > 0:
        fig = create_lcz_bar_chart(city_day, metric='SUHI', show_day_night=False, 
                                   title=f'☀️ Daytime SUHI by LCZ')
        st.plotly_chart(fig, use_container_width=True, key="day_lcz")
    else:
        st.info("No daytime data available")

with col2:
    if len(city_night) > 0:
        fig = create_lcz_bar_chart(city_night, metric='SUHI', show_day_night=False,
                                   title=f'🌙 Nighttime SUHI by LCZ')
        st.plotly_chart(fig, use_container_width=True, key="night_lcz")
    else:
        st.info("No nighttime data available")

# Day-Night difference by LCZ
st.markdown("---")
st.markdown("### 📊 Day-Night Difference by LCZ Class")

# Calculate differences
if len(city_day) > 0 and len(city_night) > 0:
    day_by_lcz = city_day.groupby('LCZ_Class')['SUHI'].mean()
    night_by_lcz = city_night.groupby('LCZ_Class')['SUHI'].mean()
    
    # Align indices
    all_lcz = sorted(set(day_by_lcz.index) | set(night_by_lcz.index))
    
    diff_data = []
    for lcz in all_lcz:
        day_val = day_by_lcz.get(lcz, 0)
        night_val = night_by_lcz.get(lcz, 0)
        diff_data.append({
            'LCZ_Class': int(lcz),
            'Day': day_val,
            'Night': night_val,
            'Difference': day_val - night_val
        })
    
    diff_df = pd.DataFrame(diff_data)
    
    # Create grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Day',
        x=diff_df['LCZ_Class'],
        y=diff_df['Day'],
        marker_color='#f39c12'
    ))
    
    fig.add_trace(go.Bar(
        name='Night',
        x=diff_df['LCZ_Class'],
        y=diff_df['Night'],
        marker_color='#2c3e50'
    ))
    
    fig.update_layout(
        title=f'SUHI by LCZ Class - Day vs Night ({city}, {season.capitalize()} {year})',
        xaxis_title='LCZ Class',
        yaxis_title='SUHI (°C)',
        barmode='group',
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True, key="day_night_comparison")
    
    # Difference bar chart
    fig2 = px.bar(
        diff_df,
        x='LCZ_Class',
        y='Difference',
        color='Difference',
        color_continuous_scale='RdBu_r',
        color_continuous_midpoint=0,
        title='Day-Night SUHI Difference by LCZ Class'
    )
    fig2.update_layout(
        xaxis_title='LCZ Class',
        yaxis_title='Day - Night Difference (°C)',
        template='plotly_white'
    )
    st.plotly_chart(fig2, use_container_width=True, key="difference_chart")

# Multi-city Day-Night comparison
st.markdown("---")
st.markdown("### 🏙️ Multi-City Day-Night Pattern")

# Get data for all cities
all_cities_data = filter_data(df, year=year, season=season)

# Calculate day-night difference by city
city_diff = []
for c in cities:
    c_day = all_cities_data[(all_cities_data['City'] == c) & (all_cities_data['Time'] == 'Day')]['SUHI'].mean()
    c_night = all_cities_data[(all_cities_data['City'] == c) & (all_cities_data['Time'] == 'Night')]['SUHI'].mean()
    if pd.notna(c_day) and pd.notna(c_night):
        city_diff.append({
            'City': c,
            'Day SUHI': c_day,
            'Night SUHI': c_night,
            'Day-Night Diff': c_day - c_night
        })

city_diff_df = pd.DataFrame(city_diff).sort_values('Day-Night Diff', ascending=False)

# Highlight current city
city_diff_df['Highlight'] = city_diff_df['City'].apply(lambda x: 'Current City' if x == city else 'Other Cities')
city_diff_df['Abs_Diff'] = city_diff_df['Day-Night Diff'].abs()

# Create scatter plot
fig = px.scatter(
    city_diff_df,
    x='Day SUHI',
    y='Night SUHI',
    color='Highlight',
    color_discrete_map={'Current City': '#e74c3c', 'Other Cities': '#3498db'},
    hover_data={'City': True, 'Day SUHI': ':.2f', 'Night SUHI': ':.2f', 'Day-Night Diff': ':.2f', 'Highlight': False, 'Abs_Diff': False},
    title=f'Day vs Night SUHI Across All Cities ({season.capitalize()} {year})',
    size='Abs_Diff',
    size_max=15
)

# Add diagonal line (y=x) - equal day and night
max_val = max(city_diff_df['Day SUHI'].max(), city_diff_df['Night SUHI'].max())
min_val = min(city_diff_df['Day SUHI'].min(), city_diff_df['Night SUHI'].min())
fig.add_trace(go.Scatter(
    x=[min_val, max_val],
    y=[min_val, max_val],
    mode='lines',
    line=dict(dash='dash', color='gray', width=2),
    name='Day = Night',
    hoverinfo='skip'
))

fig.update_traces(marker=dict(line=dict(width=1, color='white')), selector=dict(mode='markers'))
fig.update_layout(
    xaxis_title='Daytime SUHI (°C)',
    yaxis_title='Nighttime SUHI (°C)',
    template='plotly_white',
    height=600,
    showlegend=True,
    legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='right', x=0.99)
)

# Add annotations for quadrants
annotations = [
    dict(x=0.02, y=0.98, xref='paper', yref='paper', 
         text='High Night<br>Low Day', showarrow=False, 
         font=dict(size=10, color='gray'), align='left'),
    dict(x=0.98, y=0.98, xref='paper', yref='paper',
         text='High Both<br>Day & Night', showarrow=False,
         font=dict(size=10, color='gray'), align='right'),
    dict(x=0.02, y=0.02, xref='paper', yref='paper',
         text='Low Both<br>Day & Night', showarrow=False,
         font=dict(size=10, color='gray'), align='left'),
    dict(x=0.98, y=0.02, xref='paper', yref='paper',
         text='High Day<br>Low Night', showarrow=False,
         font=dict(size=10, color='gray'), align='right')
]
fig.update_layout(annotations=annotations)

st.plotly_chart(fig, use_container_width=True, key="multi_city_scatter")

# Highlight current city
current_city_data = city_diff_df[city_diff_df['City'] == city]
if len(current_city_data) > 0:
    st.info(f"📍 **{city}**: Day SUHI = {current_city_data['Day SUHI'].values[0]:.2f}°C, "
            f"Night SUHI = {current_city_data['Night SUHI'].values[0]:.2f}°C, "
            f"Difference = {current_city_data['Day-Night Diff'].values[0]:.2f}°C")

# Additional bar chart for clearer comparison
st.markdown("#### Day-Night Difference Ranking")

# Get top and bottom cities for better visualization
n_cities = min(15, len(city_diff_df))
top_cities = city_diff_df.head(n_cities)

fig2 = go.Figure()

fig2.add_trace(go.Bar(
    name='Day SUHI',
    y=top_cities['City'],
    x=top_cities['Day SUHI'],
    orientation='h',
    marker_color='#f39c12',
    text=top_cities['Day SUHI'].round(2),
    textposition='outside'
))

fig2.add_trace(go.Bar(
    name='Night SUHI',
    y=top_cities['City'],
    x=top_cities['Night SUHI'],
    orientation='h',
    marker_color='#2c3e50',
    text=top_cities['Night SUHI'].round(2),
    textposition='outside'
))

fig2.update_layout(
    title=f'Top {n_cities} Cities by Day-Night SUHI Difference',
    xaxis_title='SUHI (°C)',
    yaxis_title='',
    barmode='group',
    template='plotly_white',
    height=max(400, n_cities * 30),
    showlegend=True,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)

st.plotly_chart(fig2, use_container_width=True, key="multi_city_bars")

# Top 10 cities by day-night difference
st.markdown("### 🔝 Largest Day-Night Differences")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Largest Day > Night (Stronger daytime UHI)**")
    top_day = city_diff_df.head(10)[['City', 'Day SUHI', 'Night SUHI', 'Day-Night Diff']]
    st.dataframe(top_day.round(2), use_container_width=True, hide_index=True)

with col2:
    st.markdown("**Largest Night > Day (Stronger nighttime UHI)**")
    top_night = city_diff_df.tail(10).iloc[::-1][['City', 'Day SUHI', 'Night SUHI', 'Day-Night Diff']]
    st.dataframe(top_night.round(2), use_container_width=True, hide_index=True)
