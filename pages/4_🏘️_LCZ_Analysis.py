"""
LCZ Analysis - Local Climate Zone specific analysis
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.data_loader import (
    load_analysis_data, get_cities_list, get_regions_list, 
    filter_data, get_lcz_name, get_lcz_color, LCZ_CLASSES
)
from utils.chart_utils import (
    create_temporal_trend, create_violin_plot, create_scatter_coupling,
    LCZ_COLORS, REGION_COLORS
)

st.set_page_config(page_title="LCZ Analysis", page_icon="🏘️", layout="wide")

st.title("🏘️ LCZ Analysis")
st.markdown("Analyze urban climate patterns by Local Climate Zone")

# Load data
@st.cache_data
def load_data():
    return load_analysis_data()

df = load_data()

# Sidebar filters
st.sidebar.header("🔧 Filters")

# LCZ class selection
lcz_options = {f"LCZ {int(k)}: {v[0]}": int(k) for k, v in LCZ_CLASSES.items() if k <= 10}
selected_lcz_label = st.sidebar.selectbox(
    "Select LCZ Class",
    options=list(lcz_options.keys()),
    index=2  # Default to LCZ 3
)
selected_lcz = lcz_options[selected_lcz_label]

# Season and time filters
season = st.sidebar.selectbox("Season", options=['summer', 'winter', 'spring', 'fall', 'annual'], index=0)
time_of_day = st.sidebar.selectbox("Time of Day", options=['Day', 'Night'], index=0)

# Filter data for selected LCZ
lcz_data = filter_data(df, lcz_class=selected_lcz, season=season, time=time_of_day)
all_lcz_data = filter_data(df, season=season, time=time_of_day)

# Header with LCZ info
lcz_name = get_lcz_name(selected_lcz)
lcz_color = get_lcz_color(selected_lcz)

st.markdown(f"""
<div style="background: linear-gradient(135deg, {lcz_color} 0%, {lcz_color}99 100%); 
            padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0;">LCZ {selected_lcz}: {lcz_name}</h2>
    <p style="margin:0.5rem 0 0 0; opacity:0.9;">
        {season.capitalize()} | {time_of_day}time Analysis
    </p>
</div>
""", unsafe_allow_html=True)

# Summary statistics
st.markdown("### 📊 Summary Statistics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    avg_suhi = lcz_data['SUHI'].mean() if len(lcz_data) > 0 else 0
    st.metric("Mean SUHI", f"{avg_suhi:.2f}°C")

with col2:
    max_suhi = lcz_data['SUHI'].max() if len(lcz_data) > 0 else 0
    st.metric("Max SUHI", f"{max_suhi:.2f}°C")

with col3:
    avg_umi = lcz_data['UMI'].mean() if len(lcz_data) > 0 else 0
    st.metric("Mean UMI", f"{avg_umi:.2f} g/kg")

with col4:
    num_cities = lcz_data['City'].nunique() if len(lcz_data) > 0 else 0
    st.metric("Cities with this LCZ", num_cities)

# Regional distribution
st.markdown("---")
st.markdown(f"### 🌍 Regional Distribution of LCZ {selected_lcz}")

col1, col2 = st.columns(2)

with col1:
    fig = create_violin_plot(
        lcz_data,
        metric='SUHI',
        group_by='Region',
        title=f'SUHI Distribution by Region (LCZ {selected_lcz})'
    )
    st.plotly_chart(fig, use_container_width=True, key="regional_violin")

with col2:
    # Box plot for UMI
    fig = px.box(
        lcz_data,
        x='Region',
        y='UMI',
        color='Region',
        color_discrete_map=REGION_COLORS,
        title=f'UMI Distribution by Region (LCZ {selected_lcz})'
    )
    fig.update_layout(template='plotly_white', showlegend=False)
    st.plotly_chart(fig, use_container_width=True, key="regional_box")

# Temporal evolution
st.markdown("---")
st.markdown(f"### 📈 Temporal Evolution (2000-2020)")

# Get all years for this LCZ
lcz_temporal = filter_data(df, lcz_class=selected_lcz, season=season, time=time_of_day)

col1, col2 = st.columns(2)

with col1:
    fig = create_temporal_trend(
        lcz_temporal,
        metric='SUHI',
        group_by='Region',
        title=f'SUHI Trend by Region (LCZ {selected_lcz})'
    )
    st.plotly_chart(fig, use_container_width=True, key="temporal_suhi")

with col2:
    fig = create_temporal_trend(
        lcz_temporal,
        metric='UMI',
        group_by='Region',
        title=f'UMI Trend by Region (LCZ {selected_lcz})'
    )
    st.plotly_chart(fig, use_container_width=True, key="temporal_umi")

# Compare all LCZ classes
st.markdown("---")
st.markdown("### 🏘️ Compare All LCZ Classes")

# Calculate mean for each LCZ
lcz_summary = all_lcz_data.groupby('LCZ_Class').agg({
    'SUHI': 'mean',
    'UMI': 'mean',
    'City': 'nunique'
}).round(2).reset_index()
lcz_summary['UDI'] = -lcz_summary['UMI']
lcz_summary['LCZ_Name'] = lcz_summary['LCZ_Class'].apply(lambda x: f"LCZ {int(x)}: {get_lcz_name(x)}")

# Highlight selected LCZ
lcz_summary['Selected'] = lcz_summary['LCZ_Class'] == selected_lcz

col1, col2 = st.columns(2)

with col1:
    # Bar chart for SUHI by LCZ
    fig = px.bar(
        lcz_summary.sort_values('LCZ_Class'),
        x='LCZ_Class',
        y='SUHI',
        color='LCZ_Class',
        color_discrete_map={k: v for k, (_, v) in LCZ_CLASSES.items() if k <= 10},
        title='Mean SUHI by LCZ Class',
        hover_data=['LCZ_Name']
    )
    fig.update_layout(
        xaxis_title='LCZ Class',
        yaxis_title='SUHI (°C)',
        template='plotly_white',
        showlegend=False
    )
    # Add highlight for selected LCZ
    fig.add_vline(x=selected_lcz, line_dash='dash', line_color='black', line_width=2)
    st.plotly_chart(fig, use_container_width=True, key="all_lcz_suhi")

with col2:
    # Bar chart for UMI by LCZ
    fig = px.bar(
        lcz_summary.sort_values('LCZ_Class'),
        x='LCZ_Class',
        y='UMI',
        color='LCZ_Class',
        color_discrete_map={k: v for k, (_, v) in LCZ_CLASSES.items() if k <= 10},
        title='Mean UMI by LCZ Class',
        hover_data=['LCZ_Name']
    )
    fig.update_layout(
        xaxis_title='LCZ Class',
        yaxis_title='UMI (g/kg)',
        template='plotly_white',
        showlegend=False
    )
    fig.add_vline(x=selected_lcz, line_dash='dash', line_color='black', line_width=2)
    st.plotly_chart(fig, use_container_width=True, key="all_lcz_umi")

# Heat-moisture coupling by LCZ
st.markdown("---")
st.markdown("### 🔥💧 Heat-Moisture Coupling Analysis")

# Scatter plot with all LCZ classes
summer_all = filter_data(df, season='summer', time='Day')
fig = create_scatter_coupling(summer_all, title='SUHI vs UMI Coupling by LCZ Class (Summer Day)')
st.plotly_chart(fig, use_container_width=True, key="coupling_scatter")

# LCZ Thermal Fingerprints
st.markdown("---")
st.markdown("### 🌡️ LCZ Thermal Fingerprints by Region")

# Create 4-panel plot for each region
regions = ['Northeast', 'Midwest', 'South', 'West']

fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=regions,
    vertical_spacing=0.12,
    horizontal_spacing=0.08
)

for i, region in enumerate(regions):
    row = i // 2 + 1
    col = i % 2 + 1
    
    region_data = filter_data(all_lcz_data, region=region)
    
    if len(region_data) > 0:
        # Box plot for this region
        for lcz in sorted(region_data['LCZ_Class'].unique()):
            lcz_subset = region_data[region_data['LCZ_Class'] == lcz]
            fig.add_trace(
                go.Box(
                    y=lcz_subset['SUHI'],
                    name=f'LCZ {int(lcz)}',
                    marker_color=get_lcz_color(lcz),
                    showlegend=(i == 0)
                ),
                row=row, col=col
            )

fig.update_layout(
    height=600,
    template='plotly_white',
    title='SUHI Distribution by LCZ and Region'
)

for i in range(1, 5):
    fig.update_yaxes(title_text='SUHI (°C)', row=(i-1)//2+1, col=(i-1)%2+1)

st.plotly_chart(fig, use_container_width=True, key="thermal_fingerprints")

# Top/Bottom Cities for selected LCZ
st.markdown("---")
st.markdown(f"### 🏆 Top/Bottom Cities for LCZ {selected_lcz}")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**🔥 Hottest (High SUHI)**")
    top_hot = lcz_data.groupby('City')['SUHI'].mean().nlargest(5).reset_index()
    top_hot.columns = ['City', 'Mean SUHI (°C)']
    top_hot['Mean SUHI (°C)'] = top_hot['Mean SUHI (°C)'].round(2)
    st.dataframe(top_hot, use_container_width=True, hide_index=True)

with col2:
    st.markdown("**❄️ Coolest (Low SUHI)**")
    top_cool = lcz_data.groupby('City')['SUHI'].mean().nsmallest(5).reset_index()
    top_cool.columns = ['City', 'Mean SUHI (°C)']
    top_cool['Mean SUHI (°C)'] = top_cool['Mean SUHI (°C)'].round(2)
    st.dataframe(top_cool, use_container_width=True, hide_index=True)

# LCZ Class Legend
st.markdown("---")
st.markdown("### 📋 LCZ Class Reference")

lcz_cols = st.columns(5)
for i, (lcz_num, (lcz_name, lcz_color)) in enumerate(LCZ_CLASSES.items()):
    if lcz_num <= 10:
        with lcz_cols[i % 5]:
            is_selected = lcz_num == selected_lcz
            border = "3px solid black" if is_selected else "none"
            st.markdown(
                f'<div style="background-color:{lcz_color}; padding:8px; border-radius:5px; '
                f'margin:2px; border:{border};">'
                f'<span style="color:white; font-weight:bold;">LCZ {lcz_num}</span><br>'
                f'<small style="color:white;">{lcz_name}</small></div>',
                unsafe_allow_html=True
            )
