# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.title("Boston Crime Forecasting Dashboard")

view_map = st.sidebar.checkbox("Show District Map")

if view_map:
    st.subheader("Boston Police Districts Map")
    st.image("images/map.png", caption="Boston Police District Codes and Their Locations")

# Get available districts
forecast_dir = "forecasts"
if not os.path.exists(forecast_dir):
    st.write("No forecast data available. Please run `make forecast` first.")
else:
    available_districts = [f.split("_")[0] for f in os.listdir(forecast_dir) if f.endswith("_forecast.csv")]
    available_districts = list(set(available_districts))

    district = st.selectbox("Select District", available_districts)

    # Load forecast and test data
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
    else:
        st.write(f"No data available for district {district}.")
