"""
Chart utilities for Urban Climate Explorer using Plotly
"""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Custom color schemes
SUHI_COLORS = ['#2166ac', '#67a9cf', '#d1e5f0', '#fddbc7', '#ef8a62', '#b2182b']
UMI_COLORS = ['#8c510a', '#d8b365', '#c7eae5', '#5ab4ac', '#01665e']
REGION_COLORS = {
    'Northeast': '#e74c3c',
    'Midwest': '#3498db',
    'South': '#2ecc71',
    'West': '#f39c12'
}

# LCZ colors
LCZ_COLORS = {
    1: '#8c0000', 2: '#d10000', 3: '#ff0000', 4: '#bf4d00', 5: '#ff6600',
    6: '#ff9955', 7: '#faee05', 8: '#bcbcbc', 9: '#ffccaa', 10: '#555555'
}


def create_temporal_trend(df, metric='SUHI', group_by='City', title=None):
    """
    Create line chart showing temporal trends.
    
    Args:
        df: Filtered DataFrame with Year column
        metric: 'SUHI', 'UMI', or 'UDI'
        group_by: Column to group lines by
        title: Optional title
    """
    # Aggregate by year and group
    agg_df = df.groupby(['Year', group_by])[metric].mean().reset_index()
    
    fig = px.line(
        agg_df,
        x='Year',
        y=metric,
        color=group_by,
        markers=True,
        title=title or f'{metric} Temporal Trend (2000-2020)',
        color_discrete_map=REGION_COLORS if group_by == 'Region' else None
    )
    
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title=f'{metric} (°C)' if metric == 'SUHI' else f'{metric} (g/kg)',
        legend_title=group_by,
        hovermode='x unified',
        template='plotly_white'
    )
    
    fig.update_xaxes(tickvals=[2000, 2005, 2010, 2015, 2020])
    
    return fig


def create_seasonal_heatmap(df, metric='SUHI', title=None):
    """
    Create heatmap showing seasonal patterns over years.
    
    Args:
        df: Filtered DataFrame with Season, Year, Time columns
        metric: 'SUHI', 'UMI', or 'UDI'
        title: Optional title
    """
    # Create pivot table
    seasons_order = ['winter', 'spring', 'summer', 'fall', 'annual']
    
    # Aggregate
    agg_df = df.groupby(['Season', 'Year', 'Time'])[metric].mean().reset_index()
    
    # Create separate heatmaps for Day and Night
    fig = make_subplots(rows=1, cols=2, subplot_titles=['Daytime', 'Nighttime'])
    
    for i, time in enumerate(['Day', 'Night'], 1):
        time_df = agg_df[agg_df['Time'] == time]
        pivot = time_df.pivot(index='Season', columns='Year', values=metric)
        pivot = pivot.reindex(seasons_order)
        
        heatmap = go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='RdBu_r' if metric == 'SUHI' else 'BrBG',
            zmid=0,
            showscale=(i == 2),  # Only show colorbar for the second heatmap
            colorbar=dict(title=metric, x=1.1) if i == 2 else None
        )
        fig.add_trace(heatmap, row=1, col=i)
    
    fig.update_layout(
        title=title or f'{metric} Seasonal Pattern',
        template='plotly_white',
        height=400
    )
    
    return fig


def create_lcz_bar_chart(df, metric='SUHI', show_day_night=True, title=None):
    """
    Create grouped bar chart by LCZ class.
    
    Args:
        df: Filtered DataFrame
        metric: 'SUHI', 'UMI', or 'UDI'
        show_day_night: If True, group by Day/Night
        title: Optional title
    """
    if show_day_night:
        agg_df = df.groupby(['LCZ_Class', 'Time'])[metric].mean().reset_index()
        fig = px.bar(
            agg_df,
            x='LCZ_Class',
            y=metric,
            color='Time',
            barmode='group',
            title=title or f'{metric} by LCZ Class',
            color_discrete_map={'Day': '#f39c12', 'Night': '#2c3e50'}
        )
    else:
        agg_df = df.groupby('LCZ_Class')[metric].mean().reset_index()
        # Add LCZ colors
        agg_df['color'] = agg_df['LCZ_Class'].map(LCZ_COLORS)
        
        fig = px.bar(
            agg_df,
            x='LCZ_Class',
            y=metric,
            title=title or f'{metric} by LCZ Class',
            color='LCZ_Class',
            color_discrete_map=LCZ_COLORS
        )
    
    fig.update_layout(
        xaxis_title='LCZ Class',
        yaxis_title=f'{metric} (°C)' if metric == 'SUHI' else f'{metric} (g/kg)',
        template='plotly_white',
        showlegend=show_day_night
    )
    
    return fig


def create_comparison_radar(cities_df, metrics=['SUHI', 'UMI'], title=None):
    """
    Create radar chart comparing multiple cities.
    
    Args:
        cities_df: DataFrame with City column and metrics
        metrics: List of metrics to compare
        title: Optional title
    """
    # Aggregate by city
    agg_df = cities_df.groupby('City')[metrics].mean().reset_index()
    
    fig = go.Figure()
    
    for idx, row in agg_df.iterrows():
        fig.add_trace(go.Scatterpolar(
            r=[row[m] for m in metrics],
            theta=metrics,
            fill='toself',
            name=row['City']
        ))
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        title=title or 'City Comparison',
        template='plotly_white'
    )
    
    return fig


def create_violin_plot(df, metric='SUHI', group_by='Region', title=None):
    """
    Create violin plot showing distribution by group.
    
    Args:
        df: DataFrame with data
        metric: 'SUHI', 'UMI', or 'UDI'
        group_by: Column to group by
        title: Optional title
    """
    fig = px.violin(
        df,
        x=group_by,
        y=metric,
        color=group_by,
        box=True,
        points='outliers',
        title=title or f'{metric} Distribution by {group_by}',
        color_discrete_map=REGION_COLORS if group_by == 'Region' else None
    )
    
    fig.update_layout(
        xaxis_title=group_by,
        yaxis_title=f'{metric} (°C)' if metric == 'SUHI' else f'{metric} (g/kg)',
        template='plotly_white',
        showlegend=False
    )
    
    return fig


def create_scatter_coupling(df, title=None):
    """
    Create scatter plot showing SUHI-UMI coupling.
    
    Args:
        df: DataFrame with SUHI and UMI columns
        title: Optional title
    """
    fig = px.scatter(
        df,
        x='SUHI',
        y='UMI',
        color='LCZ_Class',
        size_max=10,
        title=title or 'Heat-Moisture Coupling',
        color_discrete_map=LCZ_COLORS,
        hover_data=['City', 'Year', 'Season']
    )
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    fig.add_vline(x=0, line_dash='dash', line_color='gray')
    
    # Add quadrant labels
    fig.add_annotation(x=5, y=3, text="Hot & Wet", showarrow=False, font=dict(size=10, color='gray'))
    fig.add_annotation(x=5, y=-3, text="Hot & Dry", showarrow=False, font=dict(size=10, color='gray'))
    fig.add_annotation(x=-5, y=3, text="Cool & Wet", showarrow=False, font=dict(size=10, color='gray'))
    fig.add_annotation(x=-5, y=-3, text="Cool & Dry", showarrow=False, font=dict(size=10, color='gray'))
    
    fig.update_layout(
        xaxis_title='SUHI (°C)',
        yaxis_title='UMI (g/kg)',
        template='plotly_white'
    )
    
    return fig


def create_lcz_composition_pie(df, year=2020, title=None):
    """
    Create pie chart showing LCZ composition.
    
    Args:
        df: DataFrame with LCZ_Class column
        year: Year to show
        title: Optional title
    """
    year_df = df[df['Year'] == year] if 'Year' in df.columns else df
    
    # Count pixels/occurrences by LCZ
    lcz_counts = year_df['LCZ_Class'].value_counts().sort_index()
    
    # Create color list
    colors = [LCZ_COLORS.get(int(lcz), '#808080') for lcz in lcz_counts.index]
    
    fig = px.pie(
        values=lcz_counts.values,
        names=[f'LCZ {int(lcz)}' for lcz in lcz_counts.index],
        title=title or f'LCZ Composition ({year})',
        color_discrete_sequence=colors
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    
    return fig


def create_ranking_chart(df, metric='SUHI', top_n=15, ascending=False, title=None):
    """
    Create horizontal bar chart ranking cities.
    
    Args:
        df: DataFrame with City column
        metric: Metric to rank by
        top_n: Number of cities to show
        ascending: Sort order
        title: Optional title
    """
    # Aggregate by city
    agg_df = df.groupby('City')[metric].mean().reset_index()
    agg_df = agg_df.sort_values(metric, ascending=ascending).head(top_n)
    
    # Color by value
    fig = px.bar(
        agg_df,
        x=metric,
        y='City',
        orientation='h',
        title=title or f'Top {top_n} Cities by {metric}',
        color=metric,
        color_continuous_scale='RdBu_r' if metric == 'SUHI' else 'BrBG'
    )
    
    fig.update_layout(
        xaxis_title=f'{metric} (°C)' if metric == 'SUHI' else f'{metric} (g/kg)',
        yaxis_title='',
        template='plotly_white',
        height=400 + top_n * 20
    )
    
    return fig


def create_metrics_cards_data(df, city=None):
    """
    Calculate summary metrics for display cards.
    
    Args:
        df: DataFrame with metrics
        city: Optional city filter
    
    Returns:
        dict with metric values
    """
    if city:
        df = df[df['City'] == city]
    
    # Get summer day values (typically strongest signal)
    summer_day = df[(df['Season'] == 'summer') & (df['Time'] == 'Day')]
    summer_night = df[(df['Season'] == 'summer') & (df['Time'] == 'Night')]
    
    return {
        'suhi_day': summer_day['SUHI'].mean() if len(summer_day) > 0 else 0,
        'suhi_night': summer_night['SUHI'].mean() if len(summer_night) > 0 else 0,
        'umi_day': summer_day['UMI'].mean() if len(summer_day) > 0 else 0,
        'umi_night': summer_night['UMI'].mean() if len(summer_night) > 0 else 0,
        'udi_day': -summer_day['UMI'].mean() if len(summer_day) > 0 else 0,
        'udi_night': -summer_night['UMI'].mean() if len(summer_night) > 0 else 0,
        'max_suhi': df['SUHI'].max() if len(df) > 0 else 0,
        'min_suhi': df['SUHI'].min() if len(df) > 0 else 0,
        'avg_suhi': df['SUHI'].mean() if len(df) > 0 else 0
    }
