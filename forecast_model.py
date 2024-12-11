# forecast_model.py
import pandas as pd
from data_prep import load_and_preprocess_data
from prophet import Prophet
import joblib
import os

if __name__ == "__main__":
    # Load and preprocess daily counts by district
    daily_counts = load_and_preprocess_data()

    # Create the forecasts directory if it doesn't exist
    os.makedirs("forecasts", exist_ok=True)

    # Define training and testing cutoff dates
    train_start = pd.Timestamp("2023-01-01")
    train_end = pd.Timestamp("2024-05-31")  # Training through end of May 2024
    test_end = pd.Timestamp("2024-10-31")   # Test through end of October 2024

    # Future forecasting period (2 months): December 2024 and January 2025
    future_start = pd.Timestamp("2024-12-01")
    future_end = pd.Timestamp("2025-01-31")

    # Get unique districts
    districts = daily_counts['DISTRICT'].unique()

    for district in districts:
        print(f"Processing district: {district}")
        df = daily_counts[daily_counts['DISTRICT'] == district].copy()

        # Prophet requires 'ds' (date) and 'y' (value) columns
        df.rename(columns={'DATE': 'ds', 'COUNT': 'y'}, inplace=True)
        df['ds'] = pd.to_datetime(df['ds'])

        # Filter data from train_start
        df = df[df['ds'] >= train_start]

        # Split data into training and testing based on the specified cutoff
        train_df = df[(df['ds'] >= train_start) & (df['ds'] <= train_end)]
        test_df = df[(df['ds'] > train_end) & (df['ds'] <= test_end)]

        # Check if we have enough training data
        if len(train_df) < 10:
            print(f"Skipping district {district} due to insufficient training data.")
            continue

        # Train the Prophet model
        model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        model.fit(train_df)

        # Forecast for the test period
        if not test_df.empty:
            # Calculate how many days to forecast for the test set
            forecast_days_test = (test_df['ds'].max() - train_end).days
            if forecast_days_test < 1:
                forecast_days_test = 30
        else:
            # No test data, just forecast 30 days beyond train_end
            forecast_days_test = 30

        future_test = model.make_future_dataframe(periods=forecast_days_test)
        forecast_test = model.predict(future_test)

        # Evaluate on test data if available
        if not test_df.empty:
            merged = pd.merge(test_df, forecast_test[['ds', 'yhat', 'yhat_lower', 'yhat_upper']], on='ds', how='left')
            mae = (merged['y'] - merged['yhat']).abs().mean()
            print(f"District {district} - Mean Absolute Error (Test: June-Oct 2024): {mae:.2f}")
            merged.to_csv(f"forecasts/{district}_test_results.csv", index=False)
        else:
            print(f"No test data available after May 2024 for district {district}.")
            merged = None

        # Save model and forecast for the test period
        forecast_test.to_csv(f"forecasts/{district}_forecast.csv", index=False)
        joblib.dump(model, f"forecasts/{district}_prophet_model.joblib")
        print(f"Test period forecast saved for district {district}.")

        # Now forecast the next 2 months (Dec 2024 & Jan 2025)
        # Calculate total days from train_end to future_end
        total_days_future = (future_end - train_end).days
        if total_days_future < 1:
            print("Future end date is before training end date, adjust your dates.")
            continue

        future_all = model.make_future_dataframe(periods=total_days_future)
        forecast_future = model.predict(future_all)

        # Filter forecast to only Dec 2024 and Jan 2025
        forecast_2months = forecast_future[(forecast_future['ds'] >= future_start) & (forecast_future['ds'] <= future_end)]
        print(f"Predictions for {district} (December 2024 - January 2025):")
        print(forecast_2months[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])

        # Optionally, save the long-term forecast
        forecast_2months.to_csv(f"forecasts/{district}_2months_future_forecast.csv", index=False)
        print(f"2-month future forecast saved for district {district}.")
