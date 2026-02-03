"""
LCZ-HeatMoist - Main Application
Interactive visualization of Urban Heat, Moisture, and Dry Islands for 50 US cities
"""
import streamlit as st
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.data_loader import load_analysis_data, load_city_boundaries, get_cities_list, get_regions_list
from utils.chart_utils import create_metrics_cards_data

# Page configuration
st.set_page_config(
    page_title="LCZ-HeatMoist",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dashboard look
st.markdown("""
<style>
    /* Main styling */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
    }
    
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Header styling */
    .app-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    
    .app-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    
    .app-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.8;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Card containers */
    .stat-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    /* Info boxes */
    .info-box {
        background: #f0f4f8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="app-header">
    <h1>🌡️ LCZ-HeatMoist</h1>
    <p>Interactive visualization of Surface Urban Heat Island (SUHI), Urban Moisture Island (UMI), and Urban Dry Island (UDI) across 50 US cities by Local Climate Zones (2000-2020)</p>
</div>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_data():
    return load_analysis_data()

df = load_data()

# Sidebar with app info
with st.sidebar:
    st.markdown("### 📊 Navigation")
    st.markdown("""
    Use the pages in the sidebar to explore:
    
    - **🗺️ CONUS Explorer**: View all cities on a map
    - **🏙️ City Explorer**: Deep-dive into a single city
    - **📊 City Comparison**: Compare multiple cities
    - **🏘️ LCZ Analysis**: Analyze by Local Climate Zone
    """)
    
    st.markdown("---")
    st.markdown("### 📈 Quick Stats")
    st.metric("Total Cities", f"{df['City'].nunique()}")
    st.metric("Years Covered", "2000-2020")
    st.metric("Total Records", f"{len(df):,}")

# Main dashboard
col1, col2, col3, col4 = st.columns(4)

# Calculate overall metrics
metrics = create_metrics_cards_data(df)

with col1:
    st.markdown("""
    <div class="metric-card" style="background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
        <h3>☀️ Avg SUHI (Day)</h3>
        <div class="value">{:.1f}°C</div>
    </div>
    """.format(metrics['suhi_day']), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="metric-card" style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);">
        <h3>🌙 Avg SUHI (Night)</h3>
        <div class="value">{:.1f}°C</div>
    </div>
    """.format(metrics['suhi_night']), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card" style="background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);">
        <h3>💧 Avg UMI (Day)</h3>
        <div class="value">{:.1f} g/kg</div>
    </div>
    """.format(metrics['umi_day']), unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="metric-card" style="background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);">
        <h3>🏜️ Avg UDI (Day)</h3>
        <div class="value">{:.1f} g/kg</div>
    </div>
    """.format(metrics['udi_day']), unsafe_allow_html=True)

# Overview charts
st.markdown("### 📊 Overview")

col1, col2 = st.columns(2)

with col1:
    # Regional distribution
    from utils.chart_utils import create_violin_plot
    fig = create_violin_plot(
        df[(df['Season'] == 'summer') & (df['Time'] == 'Day')],
        metric='SUHI',
        group_by='Region',
        title='Summer Daytime SUHI by Region'
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Top cities
    from utils.chart_utils import create_ranking_chart
    summer_day = df[(df['Season'] == 'summer') & (df['Time'] == 'Day')]
    fig = create_ranking_chart(
        summer_day,
        metric='SUHI',
        top_n=10,
        ascending=False,
        title='Top 10 Cities by Summer Daytime SUHI'
    )
    st.plotly_chart(fig, use_container_width=True)

# Information section
st.markdown("---")
st.markdown("### ℹ️ About This App")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **🌡️ SUHI (Surface Urban Heat Island)**
    
    Temperature difference between urban and rural areas:
    - **SUHI = T_urban - T_rural**
    - Positive values = urban areas warmer
    - Typically strongest in summer daytime
    """)

with col2:
    st.markdown("""
    **💧 UMI (Urban Moisture Island)**
    
    Humidity difference between urban and rural areas:
    - **UMI = H_urban - H_rural**
    - Positive values = urban areas more humid
    - Varies by vegetation and land cover
    """)

with col3:
    st.markdown("""
    **🏜️ UDI (Urban Dry Island)**
    
    Opposite of UMI, indicates moisture deficit:
    - **UDI = -UMI**
    - Positive values = urban areas drier
    - Common in highly paved areas
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Data: MODIS LST, ERA5-Land Humidity, LCZ Classification (2000-2020)</p>
    <p>50 US Cities | Seasonal Analysis | Day/Night Patterns</p>
</div>
""", unsafe_allow_html=True)
