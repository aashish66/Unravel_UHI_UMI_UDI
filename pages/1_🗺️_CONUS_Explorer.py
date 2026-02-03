"""
CONUS Explorer - View all 50 cities on an interactive map
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import (
    load_analysis_data, load_city_boundaries, load_conus_states, 
    load_regions, get_lcz_name, get_lcz_color
)
from utils.map_utils import create_base_map, add_city_markers, add_state_boundaries, add_region_boundaries
from utils.chart_utils import create_temporal_trend, create_violin_plot, create_ranking_chart
from streamlit_folium import st_folium
import folium
import pandas as pd
import branca.colormap as cm

st.set_page_config(page_title="CONUS Explorer", page_icon="🗺️", layout="wide")

st.title("🗺️ CONUS Explorer")
st.markdown("View and compare climate metrics across all 50 US cities")

# Load data
@st.cache_data
def load_data():
    df = load_analysis_data()
    gdf = load_city_boundaries()
    states = load_conus_states()
    return df, gdf, states

df, cities_gdf, states_gdf = load_data()

# Sidebar filters
st.sidebar.header("🔧 Filters")

year = st.sidebar.selectbox(
    "Year",
    options=[2000, 2005, 2010, 2015, 2020],
    index=4  # Default to 2020
)

season = st.sidebar.selectbox(
    "Season",
    options=['annual', 'winter', 'spring', 'summer', 'fall'],
    index=3  # Default to summer
)

time_of_day = st.sidebar.selectbox(
    "Time of Day",
    options=['Day', 'Night'],
    index=0
)

metric = st.sidebar.selectbox(
    "Metric to Display",
    options=['SUHI', 'UMI', 'UDI'],
    index=0
)

# Filter data
filtered_df = df[
    (df['Year'] == year) & 
    (df['Season'] == season) & 
    (df['Time'] == time_of_day)
]

# Aggregate by city
city_metrics = filtered_df.groupby('City').agg({
    'SUHI': 'mean',
    'UMI': 'mean',
    'Region': 'first'
}).reset_index()
city_metrics['UDI'] = -city_metrics['UMI']

# Merge with geometry
cities_with_metrics = cities_gdf.merge(city_metrics, on='City', how='left')

# Create map
st.markdown(f"### Showing: **{metric}** | {season.capitalize()} {year} | {time_of_day}time")

col1, col2 = st.columns([2, 1])

with col1:
    # Create folium map
    m = create_base_map(center=[39.8283, -98.5795], zoom=4)
    
    # Add state boundaries
    add_state_boundaries(m, states_gdf)
    
    # Create colormap based on metric
    valid_values = cities_with_metrics[metric].dropna()
    if len(valid_values) > 0:
        vmin, vmax = valid_values.min(), valid_values.max()
        
        if metric == 'SUHI':
            colormap = cm.LinearColormap(
                colors=['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b'],
                vmin=vmin, vmax=vmax,
                caption=f'{metric} (°C)'
            )
        elif metric == 'UMI':
            colormap = cm.LinearColormap(
                colors=['#8c510a', '#d8b365', '#f6e8c3', '#f5f5f5', '#c7eae5', '#5ab4ac', '#01665e'],
                vmin=vmin, vmax=vmax,
                caption=f'{metric} (g/kg)'
            )
        else:  # UDI
            colormap = cm.LinearColormap(
                colors=['#01665e', '#5ab4ac', '#c7eae5', '#f5f5f5', '#f6e8c3', '#d8b365', '#8c510a'],
                vmin=vmin, vmax=vmax,
                caption=f'{metric} (g/kg)'
            )
        colormap.add_to(m)
        
        # Add city markers
        for idx, row in cities_with_metrics.iterrows():
            if pd.notna(row[metric]):
                centroid = row.geometry.centroid
                color = colormap(row[metric])
                
                popup_html = f"""
                <b>{row['City']}</b><br>
                Region: {row.get('Region', 'N/A')}<br>
                SUHI: {row['SUHI']:.2f}°C<br>
                UMI: {row['UMI']:.2f} g/kg<br>
                UDI: {row['UDI']:.2f} g/kg<br>
                Pop 2020: {row.get('Census2020', 'N/A'):,.0f}
                """
                
                folium.CircleMarker(
                    location=[centroid.y, centroid.x],
                    radius=10,
                    color='white',
                    weight=2,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{row['City']}: {row[metric]:.2f}"
                ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Display map
    st_folium(m, width=800, height=500)

with col2:
    st.markdown("### 📊 Regional Statistics")
    
    # Regional summary
    regional_stats = city_metrics.groupby('Region').agg({
        'SUHI': ['mean', 'std'],
        'UMI': ['mean', 'std']
    }).round(2)
    regional_stats.columns = ['SUHI Mean', 'SUHI Std', 'UMI Mean', 'UMI Std']
    regional_stats['UDI Mean'] = -regional_stats['UMI Mean']
    
    st.dataframe(regional_stats, use_container_width=True)
    
    st.markdown("### 🔝 Top 5 Cities")
    top_cities = city_metrics.nlargest(5, metric)[['City', 'Region', metric]]
    st.dataframe(top_cities, use_container_width=True, hide_index=True)
    
    st.markdown("### 🔽 Bottom 5 Cities")
    bottom_cities = city_metrics.nsmallest(5, metric)[['City', 'Region', metric]]
    st.dataframe(bottom_cities, use_container_width=True, hide_index=True)

# Year comparison section
st.markdown("---")
st.markdown("### 📈 Temporal Comparison (2000 vs 2020)")

col1, col2 = st.columns(2)

with col1:
    # 2000 data
    df_2000 = df[(df['Year'] == 2000) & (df['Season'] == season) & (df['Time'] == time_of_day)]
    agg_2000 = df_2000.groupby('Region')[metric if metric != 'UDI' else 'UMI'].mean()
    if metric == 'UDI':
        agg_2000 = -agg_2000
    
    st.markdown("**Year 2000**")
    for region, value in agg_2000.items():
        delta_color = "normal" if metric == 'SUHI' else "inverse"
        st.metric(region, f"{value:.2f}")

with col2:
    # 2020 data
    df_2020 = df[(df['Year'] == 2020) & (df['Season'] == season) & (df['Time'] == time_of_day)]
    agg_2020 = df_2020.groupby('Region')[metric if metric != 'UDI' else 'UMI'].mean()
    if metric == 'UDI':
        agg_2020 = -agg_2020
    
    st.markdown("**Year 2020**")
    for region, value in agg_2020.items():
        change = value - agg_2000.get(region, value)
        st.metric(region, f"{value:.2f}", f"{change:+.2f}")

# Trend chart
st.markdown("### 📉 20-Year Trend by Region")

trend_data = df[(df['Season'] == season) & (df['Time'] == time_of_day)]
if metric == 'UDI':
    trend_data = trend_data.copy()
    trend_data['UDI'] = -trend_data['UMI']

fig = create_temporal_trend(trend_data, metric=metric, group_by='Region')
st.plotly_chart(fig, use_container_width=True)
