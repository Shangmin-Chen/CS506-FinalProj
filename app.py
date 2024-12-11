# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import numpy as np
import logging
import matplotlib.pyplot as plt
from shapely.geometry import Point
import geopandas as gpd
import contextily as ctx
from sklearn.cluster import DBSCAN
from prophet import Prophet

from preprocess_for_crime import preprocess_data

# Configure logging for the app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
CRS_WGS84 = "EPSG:4326"
CRS_WEB_MERCATOR = "EPSG:3857"

# Parameters for Crime-Type Analysis
SAMPLE_SIZE = 10000
RANDOM_STATE = 42
DBSCAN_EPS = 0.0001
DBSCAN_MIN_SAMPLES = 20
TOP_N_CLUSTERS = 5
FORECAST_PERIODS = 30

st.title("Boston Crime Analysis & Forecasting Dashboard")

# Sidebar navigation
mode = st.sidebar.radio("Select Mode", ("District-Based Forecasts", "Crime-Type Analysis"))

@st.cache_data
def load_preprocessed_data():
    return preprocess_data()

def get_top_crime_types(df, n=10):
    top_crimes = df['OFFENSE_TYPE'].value_counts().head(n).index.tolist()
    return top_crimes

def load_and_sample_data(df, sample_size=SAMPLE_SIZE, random_state=RANDOM_STATE, crime_type=None):
    if crime_type:
        df = df[df['OFFENSE_TYPE'] == crime_type]
        if df.empty:
            return pd.DataFrame(), np.array([])
    if len(df) < sample_size:
        df_sample = df.copy()
    else:
        df_sample = df.sample(n=sample_size, random_state=random_state)
    coords = df_sample[['Lat', 'Long']].values
    return df_sample, coords

def perform_dbscan(coords, eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES):
    if len(coords) == 0:
        return np.array([])
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='haversine')
    coords_rad = np.radians(coords)
    cluster_labels = dbscan.fit_predict(coords_rad)
    return cluster_labels

def get_top_clusters(df, top_n=TOP_N_CLUSTERS):
    cluster_counts = df['cluster'].value_counts().head(top_n)
    top_clusters = cluster_counts.index.tolist()
    return top_clusters, cluster_counts

def forecast_crime_counts(df, cluster_id, periods=FORECAST_PERIODS):
    cluster_data = df[df['cluster'] == cluster_id].copy()
    if cluster_data.empty:
        return None, pd.DataFrame()
    
    cluster_data = cluster_data.rename(columns={'OCCURRED_ON_DATE': 'ds'})
    if cluster_data['ds'].dt.tz is not None:
        cluster_data['ds'] = cluster_data['ds'].dt.tz_convert(None)
    
    daily_counts = cluster_data.set_index('ds').resample('D').size().reset_index(name='y')
    if daily_counts['ds'].dt.tz is not None:
        daily_counts['ds'] = daily_counts['ds'].dt.tz_convert(None)
    
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    model.fit(daily_counts)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    return model, forecast

def plot_forecast(model, forecast, cluster_id):
    fig1, ax1 = plt.subplots(figsize=(10,6))
    model.plot(forecast, ax=ax1)
    ax1.set_title(f'Forecast of Daily Crime Counts for Cluster {cluster_id}')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Crime Count')
    st.pyplot(fig1)
    
    fig_components = model.plot_components(forecast)
    st.pyplot(fig_components)

def plot_hotspots(gdf, top_clusters):
    fig, ax = plt.subplots(figsize=(12,12))
    minx, miny, maxx, maxy = gdf.total_bounds
    padding = 1000
    ax.set_xlim(minx - padding, maxx + padding)
    ax.set_ylim(miny - padding, maxy + padding)
    try:
        ctx.add_basemap(
            ax,
            crs=gdf.crs.to_string(),
            source=ctx.providers.Stamen.TonerLite,
            zoom=13
        )
    except:
        try:
            ctx.add_basemap(
                ax,
                crs=gdf.crs.to_string(),
                source=ctx.providers.OpenStreetMap.Mapnik,
                zoom=13
            )
        except:
            pass
    
    gdf_top_clusters = gdf[gdf['cluster'].isin(top_clusters)]
    if gdf_top_clusters.empty:
        st.warning("No cluster data to plot.")
        return
    gdf_top_clusters.plot(
        ax=ax,
        column='cluster',
        cmap='tab10',
        markersize=50,
        alpha=0.6,
        legend=True
    )
    ax.set_title("Top Crime Hotspot Clusters")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    st.pyplot(fig)

def run_crime_type_analysis():
    st.header("Crime-Type Based Clustering and Forecasting")
    df = load_preprocessed_data()
    top_10_crimes = get_top_crime_types(df, n=10)
    selected_crime = st.selectbox("Select a Crime Type to Analyze:", top_10_crimes)

    if st.button("Run Crime-Type Analysis"):
        df_sample, coords = load_and_sample_data(df, crime_type=selected_crime)
        if len(coords) == 0:
            st.warning(f"No data found for crime type '{selected_crime}'.")
            return
        cluster_labels = perform_dbscan(coords)
        if len(cluster_labels) == 0:
            st.warning("No clusters identified.")
            return
        df_sample['cluster'] = cluster_labels
        df_clustered = df_sample[df_sample['cluster'] != -1].copy()
        if df_clustered.empty:
            st.warning("No meaningful clusters found (all noise).")
            return
        
        top_clusters, _ = get_top_clusters(df_clustered)
        if not top_clusters:
            st.warning("No top clusters identified.")
            return
        top_cluster_id = top_clusters[0]
        model, forecast = forecast_crime_counts(df_clustered, top_cluster_id)
        if model is None or forecast.empty:
            st.warning("Unable to forecast due to insufficient data in the top cluster.")
            return
        
        st.subheader(f"Forecast for {selected_crime} - Top Cluster {top_cluster_id}")
        plot_forecast(model, forecast, top_cluster_id)
        
        # Plot hotspots
        st.subheader("Hotspot Clusters Map")
        gdf = gpd.GeoDataFrame(
            df_clustered,
            geometry=gpd.points_from_xy(df_clustered.Long, df_clustered.Lat),
            crs=CRS_WGS84
        ).to_crs(CRS_WEB_MERCATOR)
        plot_hotspots(gdf, top_clusters)

def run_district_analysis():
    st.header("District-Based Forecasting")
    # Always show the district map
    st.subheader("Boston Police Districts Map")
    st.image("images/map.png", caption="Boston Police District Codes and Their Locations")

    forecast_dir = "forecasts"
    if not os.path.exists(forecast_dir):
        st.write("No forecast data available. Please run `make forecast` first.")
    else:
        available_districts = [f.split("_")[0] for f in os.listdir(forecast_dir) if f.endswith("_forecast.csv")]
        available_districts = list(set(available_districts))

        if available_districts:
            district = st.selectbox("Select District", available_districts)
            forecast_file = f"{forecast_dir}/{district}_forecast.csv"
            test_results_file = f"{forecast_dir}/{district}_test_results.csv"

            if os.path.exists(forecast_file) and os.path.exists(test_results_file):
                forecast = pd.read_csv(forecast_file)
                test_results = pd.read_csv(test_results_file)

                # Forecast plot
                st.subheader(f"Forecasted Crime Counts for District {district}")
                fig = px.line(forecast, x='ds', y='yhat', title='Forecasted Crime Counts', labels={'ds': 'Date', 'yhat': 'Predicted Count'})
                fig.add_scatter(x=forecast['ds'], y=forecast['yhat_lower'], mode='lines', name='Lower Bound', line=dict(dash='dot'))
                fig.add_scatter(x=forecast['ds'], y=forecast['yhat_upper'], mode='lines', name='Upper Bound', line=dict(dash='dot'))
                st.plotly_chart(fig, use_container_width=True)

                # Actual vs predicted
                st.subheader("Actual vs Predicted Counts (Test Period)")
                test_fig = px.scatter(test_results, x='ds', y='y', title='Actual vs Predicted Counts', labels={'ds': 'Date', 'y': 'Actual Count'})
                test_fig.add_scatter(x=test_results['ds'], y=test_results['yhat'], mode='lines', name='Predicted')
                st.plotly_chart(test_fig, use_container_width=True)

                future_file = f"forecasts/{district}_2months_future_forecast.csv"
                if os.path.exists(future_file):
                    st.subheader("2-Month Future Forecast (Dec 2024 - Jan 2025)")
                    future_forecast = pd.read_csv(future_file)
                    # Display a line chart or a table
                    fig_future = px.line(future_forecast, x='ds', y='yhat', title='Future Forecasted Crime Counts')
                    fig_future.add_scatter(x=future_forecast['ds'], y=future_forecast['yhat_lower'], mode='lines', name='Lower Bound', line=dict(dash='dot'))
                    fig_future.add_scatter(x=future_forecast['ds'], y=future_forecast['yhat_upper'], mode='lines', name='Upper Bound', line=dict(dash='dot'))
                    st.plotly_chart(fig_future, use_container_width=True)
                else:
                    st.info("No future forecast file found for this district.")
                
            else:
                st.write(f"No data available for district {district}.")
        else:
            st.write("No districts available.")

# Main logic based on mode
if mode == "District-Based Forecasts":
    run_district_analysis()
else:
    run_crime_type_analysis()
