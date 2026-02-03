"""
Map utilities for Urban Climate Explorer using Folium
"""
import folium
from folium import plugins
import branca.colormap as cm
import geopandas as gpd
import numpy as np
from streamlit_folium import st_folium


def create_base_map(center=None, zoom=4):
    """Create a base folium map centered on CONUS"""
    if center is None:
        center = [39.8283, -98.5795]  # Center of CONUS
    
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='CartoDB positron',
        control_scale=True
    )
    
    # Add additional tile layers
    folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(m)
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite'
    ).add_to(m)
    
    return m


def add_city_markers(m, cities_gdf, values_col=None, popup_cols=None):
    """
    Add city markers to map.
    
    Args:
        m: Folium map object
        cities_gdf: GeoDataFrame with city boundaries
        values_col: Column name for coloring markers (optional)
        popup_cols: List of columns to show in popup
    """
    if values_col and values_col in cities_gdf.columns:
        # Create color scale
        vmin = cities_gdf[values_col].min()
        vmax = cities_gdf[values_col].max()
        colormap = cm.LinearColormap(
            colors=['blue', 'white', 'red'],
            vmin=vmin, vmax=vmax,
            caption=values_col
        )
        colormap.add_to(m)
    
    for idx, row in cities_gdf.iterrows():
        # Get centroid for marker placement
        centroid = row.geometry.centroid
        
        # Determine color
        if values_col and values_col in cities_gdf.columns:
            color = colormap(row[values_col])
        else:
            color = '#3366cc'
        
        # Build popup
        popup_html = f"<b>{row.get('City', 'Unknown')}</b><br>"
        if popup_cols:
            for col in popup_cols:
                if col in row.index:
                    popup_html += f"{col}: {row[col]}<br>"
        
        folium.CircleMarker(
            location=[centroid.y, centroid.x],
            radius=8,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row.get('City', 'City')
        ).add_to(m)
    
    return m


def add_city_boundary(m, city_gdf, buffer_gdf=None, city_name="City"):
    """
    Add city boundary polygon to map with optional buffer.
    
    Args:
        m: Folium map object
        city_gdf: GeoDataFrame with city boundary (single row)
        buffer_gdf: GeoDataFrame with buffered boundary (optional)
        city_name: Name for the layer
    """
    # Add buffer first (so it's behind city boundary)
    if buffer_gdf is not None:
        folium.GeoJson(
            buffer_gdf,
            name=f"{city_name} - 20km Buffer",
            style_function=lambda x: {
                'fillColor': '#f0f0f0',
                'color': '#888888',
                'weight': 2,
                'dashArray': '5, 5',
                'fillOpacity': 0.2
            }
        ).add_to(m)
    
    # Add city boundary with prominent styling
    folium.GeoJson(
        city_gdf,
        name=f"{city_name} - Urban Boundary",
        style_function=lambda x: {
            'fillColor': '#ff6b35',
            'color': '#d63031',
            'weight': 3,
            'fillOpacity': 0.3
        }
    ).add_to(m)
    
    return m


def add_state_boundaries(m, states_gdf):
    """Add state boundaries to map"""
    folium.GeoJson(
        states_gdf,
        name='State Boundaries',
        style_function=lambda x: {
            'fillColor': 'transparent',
            'color': '#666666',
            'weight': 1,
            'fillOpacity': 0
        }
    ).add_to(m)
    return m


def add_region_boundaries(m, regions_gdf):
    """Add US Census region boundaries to map"""
    # Define colors for each region
    region_colors = {
        'Northeast': '#e74c3c',
        'Midwest': '#3498db',
        'South': '#2ecc71',
        'West': '#f39c12'
    }
    
    for idx, row in regions_gdf.iterrows():
        region_name = row.get('NAME', 'Unknown')
        color = region_colors.get(region_name, '#95a5a6')
        
        folium.GeoJson(
            row.geometry.__geo_interface__,
            name=f"Region: {region_name}",
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': c,
                'weight': 2,
                'fillOpacity': 0.1
            }
        ).add_to(m)
    
    return m


def create_city_detail_map(city_gdf, buffer_gdf=None, raster_layer=None, city_name="City"):
    """
    Create detailed map for a single city with boundary and buffer.
    
    Args:
        city_gdf: GeoDataFrame with city boundary
        buffer_gdf: GeoDataFrame with buffered area
        raster_layer: Optional raster overlay
        city_name: City name
    """
    # Get centroid and bounds for map
    centroid = city_gdf.geometry.centroid.iloc[0]
    
    if buffer_gdf is not None:
        bounds = buffer_gdf.total_bounds
    else:
        bounds = city_gdf.total_bounds
    
    # Create map
    m = folium.Map(
        location=[centroid.y, centroid.x],
        zoom_start=10,
        tiles='CartoDB positron'
    )
    
    # Fit to bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    
    # Add layers
    add_city_boundary(m, city_gdf, buffer_gdf, city_name)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m


def create_comparison_map(cities_data):
    """
    Create a map with multiple cities for comparison.
    
    Args:
        cities_data: List of dicts with 'gdf' and 'name' keys
    """
    # Get combined bounds
    all_bounds = []
    for city in cities_data:
        all_bounds.append(city['gdf'].total_bounds)
    
    all_bounds = np.array(all_bounds)
    combined_bounds = [
        all_bounds[:, 0].min(),
        all_bounds[:, 1].min(),
        all_bounds[:, 2].max(),
        all_bounds[:, 3].max()
    ]
    
    # Create map
    center_lat = (combined_bounds[1] + combined_bounds[3]) / 2
    center_lon = (combined_bounds[0] + combined_bounds[2]) / 2
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles='CartoDB positron'
    )
    
    # Fit to bounds
    m.fit_bounds([[combined_bounds[1], combined_bounds[0]], 
                  [combined_bounds[3], combined_bounds[2]]])
    
    # Add each city with different colors
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
    
    for i, city in enumerate(cities_data):
        color = colors[i % len(colors)]
        folium.GeoJson(
            city['gdf'],
            name=city['name'],
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': c,
                'weight': 2,
                'fillOpacity': 0.4
            },
            tooltip=city['name']
        ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m


def create_suhi_colormap():
    """Create colormap for SUHI values"""
    return cm.LinearColormap(
        colors=['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b'],
        vmin=-5, vmax=10,
        caption='SUHI (°C)'
    )


def create_umi_colormap():
    """Create colormap for UMI values"""
    return cm.LinearColormap(
        colors=['#8c510a', '#d8b365', '#f6e8c3', '#f5f5f5', '#c7eae5', '#5ab4ac', '#01665e'],
        vmin=-5, vmax=5,
        caption='UMI (g/kg)'
    )
