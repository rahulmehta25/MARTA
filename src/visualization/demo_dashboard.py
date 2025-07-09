#!/usr/bin/env python3
"""
MARTA Demand Forecasting & Route Optimization Platform - Demo Dashboard
Comprehensive dashboard showcasing all platform capabilities
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
import numpy as np
from datetime import datetime, timedelta
import psycopg2
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="MARTA Demand Forecasting Platform",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .section-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_database_data():
    """Load data from PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            database=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        
        # Load various datasets
        stops_df = pd.read_sql("SELECT * FROM gtfs_stops", conn)
        routes_df = pd.read_sql("SELECT * FROM gtfs_routes", conn)
        unified_df = pd.read_sql("SELECT * FROM unified_data LIMIT 10000", conn)  # Sample for performance
        
        conn.close()
        return stops_df, routes_df, unified_df
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None, None, None

def create_demand_heatmap(unified_df, stops_df):
    """Create demand heatmap visualization"""
    # Aggregate demand by stop
    demand_by_stop = unified_df.groupby('stop_id').agg({
        'dwell_time_seconds': 'mean',
        'inferred_demand_level': lambda x: x.value_counts().index[0] if len(x) > 0 else 'Normal'
    }).reset_index()
    
    # Merge with stops data
    demand_heatmap = demand_by_stop.merge(stops_df, on='stop_id', how='left')
    
    # Create map
    m = folium.Map(location=[33.7490, -84.3880], zoom_start=11)
    
    # Color mapping for demand levels
    color_map = {
        'Low': 'green',
        'Normal': 'yellow', 
        'High': 'orange',
        'Overloaded': 'red'
    }
    
    for _, row in demand_heatmap.iterrows():
        color = color_map.get(row['inferred_demand_level'], 'gray')
        folium.CircleMarker(
            location=[row['stop_lat'], row['stop_lon']],
            radius=10,
            popup=f"<b>{row['stop_name']}</b><br>Demand: {row['inferred_demand_level']}<br>Avg Dwell: {row['dwell_time_seconds']:.1f}s",
            color=color,
            fill=True,
            fillOpacity=0.7
        ).add_to(m)
    
    return m

def create_time_series_analysis(unified_df):
    """Create time series analysis charts"""
    # Convert timestamp to datetime
    unified_df['timestamp'] = pd.to_datetime(unified_df['timestamp'])
    
    # Hourly demand pattern
    hourly_demand = unified_df.groupby('hour_of_day')['dwell_time_seconds'].mean().reset_index()
    
    fig_hourly = px.line(
        hourly_demand, 
        x='hour_of_day', 
        y='dwell_time_seconds',
        title='Average Demand by Hour of Day',
        labels={'hour_of_day': 'Hour', 'dwell_time_seconds': 'Average Dwell Time (seconds)'}
    )
    fig_hourly.update_layout(height=400)
    
    # Daily demand pattern
    daily_demand = unified_df.groupby('day_of_week')['dwell_time_seconds'].mean().reset_index()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_demand['day_of_week'] = pd.Categorical(daily_demand['day_of_week'], categories=day_order, ordered=True)
    daily_demand = daily_demand.sort_values('day_of_week')
    
    fig_daily = px.bar(
        daily_demand,
        x='day_of_week',
        y='dwell_time_seconds',
        title='Average Demand by Day of Week',
        labels={'day_of_week': 'Day', 'dwell_time_seconds': 'Average Dwell Time (seconds)'}
    )
    fig_daily.update_layout(height=400)
    
    return fig_hourly, fig_daily

def create_route_analysis(unified_df, routes_df):
    """Create route performance analysis"""
    # Route performance metrics
    route_performance = unified_df.groupby('route_id').agg({
        'delay_minutes': ['mean', 'std'],
        'dwell_time_seconds': 'mean',
        'inferred_demand_level': lambda x: (x == 'Overloaded').sum() / len(x) * 100
    }).reset_index()
    
    route_performance.columns = ['route_id', 'avg_delay', 'delay_std', 'avg_dwell', 'overload_percentage']
    
    # Merge with route names
    route_performance = route_performance.merge(routes_df[['route_id', 'route_short_name']], on='route_id', how='left')
    
    # Create performance chart
    fig_route = px.bar(
        route_performance,
        x='route_short_name',
        y=['avg_delay', 'avg_dwell'],
        title='Route Performance Metrics',
        barmode='group',
        labels={'value': 'Time (seconds/minutes)', 'variable': 'Metric'}
    )
    fig_route.update_layout(height=400)
    
    return fig_route, route_performance

def create_weather_analysis(unified_df):
    """Create weather impact analysis"""
    # Weather impact on demand
    weather_impact = unified_df.groupby('weather_condition').agg({
        'dwell_time_seconds': 'mean',
        'delay_minutes': 'mean'
    }).reset_index()
    
    fig_weather = px.bar(
        weather_impact,
        x='weather_condition',
        y='dwell_time_seconds',
        title='Weather Impact on Demand (Dwell Time)',
        labels={'weather_condition': 'Weather', 'dwell_time_seconds': 'Average Dwell Time (seconds)'}
    )
    fig_weather.update_layout(height=400)
    
    return fig_weather

def create_prediction_interface():
    """Create interactive prediction interface"""
    st.subheader("🔮 Demand Prediction Interface")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_stop = st.selectbox(
            "Select Stop",
            options=['Five Points Station', 'Peachtree Center', 'Midtown', 'Buckhead', 'Airport']
        )
    
    with col2:
        selected_hour = st.slider("Hour of Day", 0, 23, 8)
    
    with col3:
        selected_weather = st.selectbox(
            "Weather Condition",
            options=['Clear', 'Cloudy', 'Rainy', 'Sunny']
        )
    
    # Simulate prediction (in real system, this would call the ML model)
    base_demand = 50
    if 7 <= selected_hour <= 9 or 17 <= selected_hour <= 19:
        base_demand = 120
    elif selected_hour >= 22 or selected_hour <= 5:
        base_demand = 20
    
    if selected_weather == 'Rainy':
        base_demand *= 1.3
    elif selected_weather == 'Sunny':
        base_demand *= 0.9
    
    predicted_demand = int(base_demand + np.random.normal(0, 10))
    
    st.metric(
        label="Predicted Demand Level",
        value=f"{predicted_demand} riders",
        delta=f"{predicted_demand - 50} vs baseline"
    )

def create_optimization_interface():
    """Create route optimization interface"""
    st.subheader("🛣️ Route Optimization Simulation")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Current Route Performance**")
        st.metric("Average Delay", "3.2 minutes", delta="-0.5 minutes")
        st.metric("Overloaded Segments", "5", delta="-2")
        st.metric("Vehicle Utilization", "78%", delta="+5%")
    
    with col2:
        st.write("**Proposed Optimizations**")
        
        if st.button("🚀 Run Optimization Simulation"):
            st.success("Optimization simulation completed!")
            
            # Simulate optimization results
            st.write("**Recommended Changes:**")
            st.write("1. Add short-turn loop on Red Line (North Springs to Buckhead)")
            st.write("2. Increase frequency on Gold Line during rush hours")
            st.write("3. Reroute Bus Route 1 to serve Midtown better")
            
            st.write("**Expected Impact:**")
            st.metric("Reduced Wait Times", "-15%", delta="-2.1 minutes")
            st.metric("Improved Load Balance", "+12%", delta="+0.3")
            st.metric("Cost Savings", "$45K/month", delta="-$3.2K")

def main():
    """Main dashboard function"""
    # Header
    st.markdown('<h1 class="main-header">🚇 MARTA Demand Forecasting & Route Optimization Platform</h1>', unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading data..."):
        stops_df, routes_df, unified_df = load_database_data()
    
    if stops_df is None:
        st.error("Failed to load data. Please check database connection.")
        return
    
    # Sidebar filters
    st.sidebar.header("📊 Dashboard Filters")
    
    # Date range filter
    if not unified_df.empty:
        min_date = unified_df['timestamp'].min()
        max_date = unified_df['timestamp'].max()
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date()
        )
    
    # Route filter
    if not routes_df.empty:
        selected_routes = st.sidebar.multiselect(
            "Select Routes",
            options=routes_df['route_short_name'].unique(),
            default=routes_df['route_short_name'].unique()[:3]
        )
    
    # Main dashboard content
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", 
        "🗺️ Demand Heatmap", 
        "⏰ Time Analysis", 
        "🔮 Predictions", 
        "🛣️ Optimization"
    ])
    
    with tab1:
        st.markdown('<h2 class="section-header">Platform Overview</h2>', unsafe_allow_html=True)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Stops", len(stops_df))
        
        with col2:
            st.metric("Active Routes", len(routes_df))
        
        with col3:
            if not unified_df.empty:
                avg_delay = unified_df['delay_minutes'].mean()
                st.metric("Avg Delay", f"{avg_delay:.1f} min")
        
        with col4:
            if not unified_df.empty:
                overloaded_pct = (unified_df['inferred_demand_level'] == 'Overloaded').mean() * 100
                st.metric("Overloaded Stops", f"{overloaded_pct:.1f}%")
        
        # Recent activity
        st.subheader("📊 Recent Activity")
        if not unified_df.empty:
            recent_data = unified_df.tail(100)
            fig_recent = px.line(
                recent_data,
                x='timestamp',
                y='dwell_time_seconds',
                color='stop_id',
                title='Recent Dwell Times by Stop'
            )
            st.plotly_chart(fig_recent, use_container_width=True)
    
    with tab2:
        st.markdown('<h2 class="section-header">Demand Heatmap</h2>', unsafe_allow_html=True)
        
        if not unified_df.empty and not stops_df.empty:
            demand_map = create_demand_heatmap(unified_df, stops_df)
            folium_static(demand_map, width=800, height=600)
            
            # Demand level distribution
            demand_dist = unified_df['inferred_demand_level'].value_counts()
            fig_dist = px.pie(
                values=demand_dist.values,
                names=demand_dist.index,
                title='Demand Level Distribution'
            )
            st.plotly_chart(fig_dist, use_container_width=True)
    
    with tab3:
        st.markdown('<h2 class="section-header">Time Series Analysis</h2>', unsafe_allow_html=True)
        
        if not unified_df.empty:
            fig_hourly, fig_daily = create_time_series_analysis(unified_df)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig_hourly, use_container_width=True)
            with col2:
                st.plotly_chart(fig_daily, use_container_width=True)
            
            # Route performance
            fig_route, route_perf = create_route_analysis(unified_df, routes_df)
            st.plotly_chart(fig_route, use_container_width=True)
            
            # Weather impact
            fig_weather = create_weather_analysis(unified_df)
            st.plotly_chart(fig_weather, use_container_width=True)
    
    with tab4:
        st.markdown('<h2 class="section-header">Demand Prediction</h2>', unsafe_allow_html=True)
        create_prediction_interface()
        
        # Model performance metrics
        st.subheader("📊 Model Performance")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("RMSE", "12.3 riders", delta="-2.1")
        with col2:
            st.metric("MAE", "8.7 riders", delta="-1.5")
        with col3:
            st.metric("R² Score", "0.87", delta="+0.03")
    
    with tab5:
        st.markdown('<h2 class="section-header">Route Optimization</h2>', unsafe_allow_html=True)
        create_optimization_interface()
        
        # Optimization history
        st.subheader("📈 Optimization History")
        optimization_data = pd.DataFrame({
            'Date': pd.date_range(start='2024-01-01', periods=30, freq='D'),
            'Wait Time Reduction': np.random.normal(15, 5, 30),
            'Load Balance Improvement': np.random.normal(12, 3, 30),
            'Cost Savings': np.random.normal(45, 10, 30)
        })
        
        fig_opt = px.line(
            optimization_data,
            x='Date',
            y=['Wait Time Reduction', 'Load Balance Improvement'],
            title='Optimization Impact Over Time'
        )
        st.plotly_chart(fig_opt, use_container_width=True)

if __name__ == "__main__":
    main() 