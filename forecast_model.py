# forecast_model.py
import pandas as pd
from data_prep import load_and_preprocess_data
from prophet import Prophet
import joblib
import os

if __name__ == "__main__":
    # Load and preprocess data
    daily_counts = load_and_preprocess_data()

    # Get unique districts
    districts = daily_counts['DISTRICT'].unique()
    os.makedirs("forecasts", exist_ok=True)  # Directory to store outputs

    # Define training cutoff date
    train_cutoff = pd.Timestamp("2023-10-31")

    for district in districts:
        print(f"Processing district: {district}")
        df = daily_counts[daily_counts['DISTRICT'] == district].copy()
        
        # Prophet requires 'ds' (date) and 'y' (value) columns
        df.rename(columns={'DATE': 'ds', 'COUNT': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])
        
        # Split data into training (Jan–Oct 2023) and testing (Nov 2023 onward)
        train_df = df[df['ds'] <= train_cutoff]
        test_df = df[df['ds'] > train_cutoff]
        
        # Skip districts with insufficient training data
        if len(train_df) < 10:  # Adjust this threshold as needed
            print(f"Skipping district {district} due to insufficient data.")
            continue
        
        # Fit Prophet model
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        model.fit(train_df)
        
        # Forecast for the test period
        future = model.make_future_dataframe(periods=len(test_df))  # Match forecast length to test data
        forecast = model.predict(future)
        
        # Ensure consistency of date formats for merging
        test_df['ds'] = pd.to_datetime(test_df['ds'])
        forecast['ds'] = pd.to_datetime(forecast['ds'])
        
        # Merge forecast with test data
        merged = pd.merge(test_df, forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='left')
        mae = (merged['y'] - merged['yhat']).abs().mean()
        print(f"District {district} - Mean Absolute Error (Test): {mae:.2f}")
        
        # Save model, forecast, and test results
        joblib.dump(model, f"forecasts/{district}_prophet_model.joblib")
        forecast.to_csv(f"forecasts/{district}_forecast.csv", index=False)
        merged.to_csv(f"forecasts/{district}_test_results.csv", index=False)
        
        print(f"Forecast saved for district {district}.")
