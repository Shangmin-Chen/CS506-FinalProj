# main.py
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from prophet import Prophet
from preprocess import preprocess_data  # Ensure this module is in the same directory or PYTHONPATH
import geopandas as gpd
import contextily as ctx
from shapely.geometry import Point
import logging
import matplotlib.colors as mcolors

# Configure logging for main.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Parameters
SAMPLE_SIZE = 10000
RANDOM_STATE = 42
DBSCAN_EPS = 0.0001  # in radians (~0.057 degrees)
DBSCAN_MIN_SAMPLES = 20
TOP_N_CLUSTERS = 5
FORECAST_PERIODS = 30
CRS_WGS84 = "EPSG:4326"
CRS_WEB_MERCATOR = "EPSG:3857"

def load_and_sample_data(sample_size=SAMPLE_SIZE, random_state=RANDOM_STATE, crime_type=None):
    """
    Loads data using preprocess_data, filters by crime type, and samples a subset for clustering.
    
    Parameters:
        sample_size (int): Number of samples to draw.
        random_state (int): Seed for reproducibility.
        crime_type (str): Type of crime to filter by (e.g., 'THEFT', 'ASSAULT').
    
    Returns:
        df_sample (pd.DataFrame): Sampled and filtered DataFrame with necessary columns.
        coords (np.ndarray): Array of latitude and longitude values.
    """
    logging.info("Loading and preprocessing data...")
    df = preprocess_data()
    
    # Ensure necessary columns exist
    required_columns = ['Lat', 'Long', 'OCCURRED_ON_DATE', 'OFFENSE_TYPE']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logging.error(f"Missing columns in data: {missing_columns}")
        raise ValueError(f"Missing columns: {missing_columns}")
    
    # **Filter Data Based on Specified Crime Type**
    if crime_type:
        logging.info(f"Filtering data for crime type: {crime_type}")
        df = df[df['OFFENSE_TYPE'] == crime_type]
        logging.info(f"Number of records after filtering for '{crime_type}': {len(df)}")
        
        if df.empty:
            logging.warning(f"No data found for crime type '{crime_type}'. Exiting analysis.")
            return df, np.array([])
    
    # Sample the data
    logging.info(f"Sampling {sample_size} records from the filtered data...")
    if len(df) < sample_size:
        logging.warning(f"Requested sample size {sample_size} is larger than available data {len(df)}. Sampling all available data.")
        df_sample = df.copy()
    else:
        df_sample = df.sample(n=sample_size, random_state=random_state)
    
    coords = df_sample[['Lat', 'Long']].values
    logging.info(f"Sampled {len(df_sample)} records.")
    return df_sample, coords

def perform_dbscan(coords, eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES):
    """
    Performs DBSCAN clustering on geographic coordinates.
    
    Parameters:
        coords (np.ndarray): Array of latitude and longitude values.
        eps (float): The maximum distance between two samples for them to be considered as in the same neighborhood.
        min_samples (int): The number of samples in a neighborhood for a point to be considered as a core point.
    
    Returns:
        cluster_labels (np.ndarray): Array of cluster labels for each point.
    """
    if len(coords) == 0:
        logging.error("No coordinates provided for clustering.")
        return np.array([])
    
    logging.info("Performing DBSCAN clustering...")
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='haversine')
    coords_rad = np.radians(coords)
    cluster_labels = dbscan.fit_predict(coords_rad)
    n_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
    logging.info(f"DBSCAN identified {n_clusters} clusters (excluding noise).")
    return cluster_labels

def get_top_clusters(df, top_n=TOP_N_CLUSTERS):
    """
    Identifies the top N clusters based on the number of points in each cluster.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing cluster labels.
        top_n (int): Number of top clusters to identify.
    
    Returns:
        top_clusters (list): List of top cluster IDs.
        cluster_counts (pd.Series): Series containing counts of each top cluster.
    """
    if 'cluster' not in df.columns:
        logging.error("'cluster' column is missing from the DataFrame.")
        return [], pd.Series()
    
    logging.info("Identifying top clusters...")
    cluster_counts = df['cluster'].value_counts().head(top_n)
    top_clusters = cluster_counts.index.tolist()
    logging.info(f"Top {top_n} clusters:\n{cluster_counts}")
    return top_clusters, cluster_counts

def forecast_crime_counts(df, cluster_id, periods=FORECAST_PERIODS):
    """
    Forecasts future crime counts for a specific cluster using Prophet.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing data for the specific cluster.
        cluster_id (int): The ID of the cluster to forecast.
        periods (int): Number of days to forecast into the future.
    
    Returns:
        model (Prophet): Trained Prophet model.
        forecast (pd.DataFrame): Forecasted data.
    """
    logging.info(f"Forecasting crime counts for cluster {cluster_id}...")
    cluster_data = df[df['cluster'] == cluster_id].copy()
    
    if cluster_data.empty:
        logging.warning(f"No data available for cluster {cluster_id}.")
        return None, pd.DataFrame()
    
    # Rename 'OCCURRED_ON_DATE' to 'ds' for Prophet
    cluster_data = cluster_data.rename(columns={'OCCURRED_ON_DATE': 'ds'})
    
    # Check the dtype and timezone
    logging.info(f"'ds' dtype: {cluster_data['ds'].dtype}")
    if cluster_data['ds'].dt.tz is not None:
        logging.warning("'ds' is timezone-aware. Converting to timezone-naive.")
        cluster_data['ds'] = cluster_data['ds'].dt.tz_convert(None)
    else:
        logging.info("'ds' is already timezone-naive.")
    
    # Group by date (daily frequency) to get count of crimes per day
    logging.info("Grouping data by day to get daily crime counts...")
    daily_counts = cluster_data.set_index('ds').resample('D').size().reset_index(name='y')
    
    # Prophet expects 'ds' to be datetime and 'y' to be numeric
    logging.info(f"'ds' dtype after resampling: {daily_counts['ds'].dtype}")
    if daily_counts['ds'].dt.tz is not None:
        logging.warning("'ds' is timezone-aware after resampling. Converting to naive.")
        daily_counts['ds'] = daily_counts['ds'].dt.tz_convert(None)
    else:
        logging.info("'ds' is timezone-naive after resampling.")
    
    # Initialize and fit Prophet model
    logging.info("Initializing and fitting Prophet model...")
    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    model.fit(daily_counts)
    
    # Create future dataframe
    logging.info(f"Creating future dataframe for the next {periods} days...")
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    logging.info("Forecasting completed.")
    return model, forecast

def plot_forecast(model, forecast, cluster_id):
    """
    Plots the forecasted crime counts and their components.
    
    Parameters:
        model (Prophet): Trained Prophet model.
        forecast (pd.DataFrame): Forecasted data.
        cluster_id (int): The ID of the cluster being forecasted.
    """
    if model is None or forecast.empty:
        logging.warning("No forecast data available to plot.")
        return
    
    logging.info("Plotting forecast...")
    fig1 = model.plot(forecast)
    plt.title(f'Forecast of Daily Crime Counts for Cluster {cluster_id}')
    plt.xlabel('Date')
    plt.ylabel('Crime Count')
    plt.tight_layout()
    plt.show()
    
    logging.info("Plotting forecast components...")
    fig2 = model.plot_components(forecast)
    plt.tight_layout()
    plt.show()

def plot_hotspots(gdf, top_clusters):
    """
    Plots the top crime hotspot clusters on a map with a basemap.
    
    Parameters:
        gdf (GeoDataFrame): GeoDataFrame containing clustered data.
        top_clusters (list): List of top cluster IDs to plot.
    """
    logging.info("Plotting crime hotspots...")
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Check and log GeoDataFrame bounds
    minx, miny, maxx, maxy = gdf.total_bounds
    logging.info(f"GeoDataFrame bounds: minx={minx}, miny={miny}, maxx={maxx}, maxy={maxy}")
    
    # Define plot extent with padding
    padding = 1000  # in meters; adjust as needed
    ax.set_xlim(minx - padding, maxx + padding)
    ax.set_ylim(miny - padding, maxy + padding)
    
    # Attempt to add basemap with a valid zoom level
    try:
        logging.info("Adding Stamen Toner-Lite basemap...")
        ctx.add_basemap(
            ax,
            crs=gdf.crs.to_string(),
            source=ctx.providers.Stamen.TonerLite,
            zoom=13  # Adjust zoom level within 0-20
        )
    except Exception as e:
        logging.error(f"Failed to add Stamen Toner-Lite basemap: {e}")
        logging.info("Attempting to add OpenStreetMap basemap instead.")
        try:
            logging.info("Adding OpenStreetMap Mapnik basemap...")
            ctx.add_basemap(
                ax,
                crs=gdf.crs.to_string(),
                source=ctx.providers.OpenStreetMap.Mapnik,
                zoom=13
            )
            logging.info("Successfully added OpenStreetMap basemap.")
        except Exception as e:
            logging.error(f"Failed to add OpenStreetMap basemap: {e}")
            logging.warning("Proceeding without a basemap.")
    
    # Define a color map with distinct colors
    cmap = 'tab10'  # Choose an appropriate colormap
    
    # Filter GeoDataFrame for top clusters
    gdf_top_clusters = gdf[gdf['cluster'].isin(top_clusters)]
    
    # Check if there are clusters to plot
    if gdf_top_clusters.empty:
        logging.warning("No data available for the top clusters to plot.")
        return
    
    # Plot all top clusters at once with a color map
    logging.info("Plotting top clusters on the map...")
    gdf_top_clusters.plot(
        ax=ax,
        column='cluster',
        cmap=cmap,
        markersize=50,        # Adjust marker size as needed
        alpha=0.6,
        legend=True
    )

    
    plt.title("Top Crime Hotspot Clusters")
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.tight_layout()
    plt.show()

def main():
    try:
        # **Specify the Crime Type to Analyze**
        CRIME_TYPE = 'LARCENY SHOPLIFTING'  # Replace with desired crime type, e.g., 'ASSAULT', 'ROBBERY', etc.
        logging.info(f"Analyzing crime type: {CRIME_TYPE}")
        
        # Load, filter, and sample data
        df_sample, coords = load_and_sample_data(crime_type=CRIME_TYPE)
        
        if len(coords) == 0:
            logging.warning("No coordinates available after filtering. Exiting analysis.")
            return
        
        # Perform DBSCAN clustering
        cluster_labels = perform_dbscan(coords)
        if len(cluster_labels) == 0:
            logging.warning("Clustering was not performed due to lack of data.")
            return
        df_sample = df_sample.assign(cluster=cluster_labels)
        
        # Remove noise points (cluster label = -1)
        df_clustered = df_sample[df_sample['cluster'] != -1].copy()
        logging.info(f"Number of clustered points (excluding noise): {len(df_clustered)}")
        
        if df_clustered.empty:
            logging.warning("No clusters found after removing noise.")
            return
        
        # Identify top clusters
        top_clusters, cluster_counts = get_top_clusters(df_clustered)
        
        if not top_clusters:
            logging.warning("No top clusters identified.")
            return
        
        # Time Series Forecasting for the top cluster
        top_cluster_id = top_clusters[0]
        model, forecast = forecast_crime_counts(df_clustered, top_cluster_id)
        
        # Plot Forecast
        plot_forecast(model, forecast, top_cluster_id)
        
        # Geospatial Visualization
        logging.info("Preparing geospatial data for plotting...")
        gdf = gpd.GeoDataFrame(
            df_clustered,
            geometry=gpd.points_from_xy(df_clustered.Long, df_clustered.Lat),
            crs=CRS_WGS84
        ).to_crs(CRS_WEB_MERCATOR)
        
        plot_hotspots(gdf, top_clusters)
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
