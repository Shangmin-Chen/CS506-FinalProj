# forecast_model.py
import pandas as pd
from data_prep import load_and_preprocess_data
from prophet import Prophet
import joblib
import os

if __name__ == "__main__":
    # Load and preprocess data
    daily_counts = load_and_preprocess_data()

    # Create the forecasts directory if it doesn't exist
    os.makedirs("forecasts", exist_ok=True)

    # Define training cutoff dates
    train_start = pd.Timestamp("2023-01-01")
    train_end = pd.Timestamp("2024-05-31")  # Up to and including May 2024

    # Get unique districts
    districts = daily_counts['DISTRICT'].unique()

    for district in districts:
        print(f"Processing district: {district}")
        df = daily_counts[daily_counts['DISTRICT'] == district].copy()

        # Prophet requires 'ds' (date) and 'y' (value) columns
        df.rename(columns={'DATE': 'ds', 'COUNT': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])

        # Filter the data to ensure we only consider data starting from January 2023
        df = df[df['ds'] >= train_start]

        # Split data into training and testing based on the specified cutoff
        train_df = df[(df['ds'] >= train_start) & (df['ds'] <= train_end)]
        test_df = df[df['ds'] > train_end]

        # Check if we have enough training data
        if len(train_df) < 10:
            print(f"Skipping district {district} due to insufficient training data.")
            continue

        # Train the Prophet model
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        model.fit(train_df)

        # Forecast the length of the test period
        if not test_df.empty:
            # The number of days in the test set
            forecast_days = (test_df['ds'].max() - train_end).days
            # If test_df isn't empty but only has one day or is non-continuous,
            # adjust as needed. Here we assume continuous daily data.
            if forecast_days < 1:
                # If there's data after train_end but no full day difference, default to 30 days
                forecast_days = 30
        else:
            # If there's no test data at all, just forecast 30 days beyond train_end
            forecast_days = 30

        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)

        # Ensure date formats align
        test_df['ds'] = pd.to_datetime(test_df['ds'])
        forecast['ds'] = pd.to_datetime(forecast['ds'])

        # Merge forecast with test data (if test data is available)
        if not test_df.empty:
            merged = pd.merge(test_df, forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='left')
            mae = (merged['y'] - merged['yhat']).abs().mean()
            print(f"District {district} - Mean Absolute Error (Test): {mae:.2f}")
            merged.to_csv(f"forecasts/{district}_test_results.csv", index=False)
        else:
            print(f"No test data available after May 2024 for district {district}.")
            # If no test data, we won't compute MAE or save test results
            merged = None

        # Save model and forecast
        joblib.dump(model, f"forecasts/{district}_prophet_model.joblib")
        forecast.to_csv(f"forecasts/{district}_forecast.csv", index=False)

        print(f"Forecast saved for district {district}.")
