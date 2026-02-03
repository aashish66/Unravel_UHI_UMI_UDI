"""
City Comparison - Compare multiple cities side by side
"""
import streamlit as st
import sys
from pathlib import Path
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import (
    load_analysis_data, load_city_boundaries, get_cities_list, 
    get_regions_list, filter_data, LCZ_CLASSES
)
from utils.map_utils import create_comparison_map
from utils.chart_utils import (
    create_temporal_trend, create_lcz_bar_chart, create_comparison_radar,
    create_ranking_chart, LCZ_COLORS
)

st.set_page_config(page_title="City Comparison", page_icon="📊", layout="wide")

st.title("📊 City Comparison")
st.markdown("Compare urban climate metrics across multiple cities")

# Load data
@st.cache_data
def load_data():
    df = load_analysis_data()
    gdf = load_city_boundaries()
    return df, gdf

df, cities_gdf = load_data()

# Sidebar - City Selection
st.sidebar.header("🔧 Select Cities to Compare")

all_cities = get_cities_list()

# Multi-select cities
selected_cities = st.sidebar.multiselect(
    "Select 2-5 Cities",
    options=all_cities,
    default=['New York', 'Los Angeles', 'Chicago'],
    max_selections=5
)

if len(selected_cities) < 2:
    st.warning("⚠️ Please select at least 2 cities to compare")
    st.stop()

# Filters
year = st.sidebar.selectbox("Year", options=[2000, 2005, 2010, 2015, 2020], index=4)
season = st.sidebar.selectbox("Season", options=['summer', 'winter', 'spring', 'fall', 'annual'], index=0)
time_of_day = st.sidebar.selectbox("Time of Day", options=['Day', 'Night'], index=0)

# Filter data
comparison_df = filter_data(df, city=selected_cities, year=year, season=season, time=time_of_day)
all_years_df = filter_data(df, city=selected_cities, season=season, time=time_of_day)

# Summary metrics
st.markdown(f"### Comparing: {', '.join(selected_cities)}")
st.markdown(f"**Settings:** {season.capitalize()} {year} | {time_of_day}time")

# Quick stats table
st.markdown("---")
st.markdown("### 📊 Summary Statistics")

summary_stats = comparison_df.groupby('City').agg({
    'SUHI': 'mean',
    'UMI': 'mean',
    'Region': 'first'
}).round(2)
summary_stats['UDI'] = -summary_stats['UMI']
summary_stats = summary_stats.reset_index()

# Rank cities
summary_stats['SUHI Rank'] = summary_stats['SUHI'].rank(ascending=False).astype(int)
summary_stats['UMI Rank'] = summary_stats['UMI'].rank(ascending=False).astype(int)

# Display table
st.dataframe(
    summary_stats[['City', 'Region', 'SUHI', 'SUHI Rank', 'UMI', 'UMI Rank', 'UDI']],
    use_container_width=True,
    hide_index=True
)

# Map comparison
st.markdown("---")
st.markdown("### 🗺️ Location Map")

# Create map with all selected cities
cities_data = []
for city in selected_cities:
    city_gdf = cities_gdf[cities_gdf['City'] == city]
    if len(city_gdf) > 0:
        cities_data.append({'gdf': city_gdf, 'name': city})

if cities_data:
    m = create_comparison_map(cities_data)
    st_folium(m, width=900, height=400)

# Metric comparison charts
st.markdown("---")
st.markdown("### 📈 Metric Comparison")

col1, col2 = st.columns(2)

with col1:
    # SUHI comparison bar chart
    fig = px.bar(
        summary_stats,
        x='City',
        y='SUHI',
        color='City',
        title=f'SUHI Comparison ({season.capitalize()} {year}, {time_of_day})',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(showlegend=False, template='plotly_white')
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    st.plotly_chart(fig, use_container_width=True, key="suhi_comparison")

with col2:
    # UMI comparison bar chart
    fig = px.bar(
        summary_stats,
        x='City',
        y='UMI',
        color='City',
        title=f'UMI Comparison ({season.capitalize()} {year}, {time_of_day})',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(showlegend=False, template='plotly_white')
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    st.plotly_chart(fig, use_container_width=True, key="umi_comparison")

# Temporal trends overlay
st.markdown("---")
st.markdown("### 📉 20-Year Trends")

col1, col2 = st.columns(2)

with col1:
    fig = create_temporal_trend(
        all_years_df,
        metric='SUHI',
        group_by='City',
        title=f'SUHI Trend ({season.capitalize()}, {time_of_day})'
    )
    st.plotly_chart(fig, use_container_width=True, key="suhi_trend")

with col2:
    fig = create_temporal_trend(
        all_years_df,
        metric='UMI',
        group_by='City',
        title=f'UMI Trend ({season.capitalize()}, {time_of_day})'
    )
    st.plotly_chart(fig, use_container_width=True, key="umi_trend")

# LCZ comparison
st.markdown("---")
st.markdown("### 🏘️ LCZ Class Comparison")

# Create grouped bar chart by city and LCZ
lcz_comparison = comparison_df.groupby(['City', 'LCZ_Class'])['SUHI'].mean().reset_index()

fig = px.bar(
    lcz_comparison,
    x='LCZ_Class',
    y='SUHI',
    color='City',
    barmode='group',
    title='SUHI by LCZ Class Across Cities',
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig.update_layout(
    xaxis_title='LCZ Class',
    yaxis_title='SUHI (°C)',
    template='plotly_white'
)
st.plotly_chart(fig, use_container_width=True, key="lcz_comparison")

# Radar chart comparison
st.markdown("---")
st.markdown("### 🎯 Multi-Metric Radar Comparison")

# Calculate multiple metrics for radar
radar_data = []
for city in selected_cities:
    city_data = comparison_df[comparison_df['City'] == city]
    if len(city_data) > 0:
        radar_data.append({
            'City': city,
            'SUHI': city_data['SUHI'].mean(),
            'UMI': city_data['UMI'].mean(),
            'Max SUHI': city_data['SUHI'].max(),
            'Min SUHI': city_data['SUHI'].min()
        })

radar_df = pd.DataFrame(radar_data)

if len(radar_df) > 0:
    # Normalize values for radar chart
    metrics = ['SUHI', 'UMI', 'Max SUHI', 'Min SUHI']
    
    fig = go.Figure()
    
    for idx, row in radar_df.iterrows():
        values = [row[m] for m in metrics]
        values.append(values[0])  # Close the polygon
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics + [metrics[0]],
            fill='toself',
            name=row['City'],
            opacity=0.6
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[-5, 10])),
        showlegend=True,
        title='Multi-Metric Comparison',
        template='plotly_white'
    )
    st.plotly_chart(fig, use_container_width=True, key="radar")

# Population and socioeconomic comparison
st.markdown("---")
st.markdown("### 👥 City Characteristics")

city_chars = []
for city in selected_cities:
    city_info = cities_gdf[cities_gdf['City'] == city]
    if len(city_info) > 0:
        info = city_info.iloc[0]
        city_chars.append({
            'City': city,
            'Population 2020': info.get('Census2020', None),
            'Population 2010': info.get('Census2010', None),
            'State': info.get('State', 'N/A')
        })

if city_chars:
    chars_df = pd.DataFrame(city_chars)
    
    # Format population
    for col in ['Population 2020', 'Population 2010']:
        if col in chars_df.columns:
            chars_df[col] = chars_df[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
    
    st.dataframe(chars_df, use_container_width=True, hide_index=True)

# Download comparison data
st.markdown("---")
with st.expander("📥 Download Comparison Data"):
    csv = comparison_df.to_csv(index=False)
    st.download_button(
        label="Download Full Comparison CSV",
        data=csv,
        file_name=f"city_comparison_{'_'.join(selected_cities)}.csv",
        mime="text/csv"
    )
