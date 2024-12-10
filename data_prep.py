# data_prep.py
import pandas as pd

def load_and_preprocess_data(file_path="Boston Data.csv"):
    # Load data
    data = pd.read_csv(file_path, encoding='latin', low_memory=False)
    
    # Ensure OCCURRED_ON_DATE is datetime
    data['OCCURRED_ON_DATE'] = pd.to_datetime(data['OCCURRED_ON_DATE'], errors='coerce')
    data.dropna(subset=['OCCURRED_ON_DATE'], inplace=True)
    
    # If DISTRICT is missing, fill with 'UNKNOWN'
    if 'DISTRICT' not in data.columns:
        data['DISTRICT'] = 'UNKNOWN'
    data['DISTRICT'] = data['DISTRICT'].fillna('UNKNOWN')
    
    # Aggregate daily crime counts by district
    daily_counts = data.groupby(['DISTRICT', data['OCCURRED_ON_DATE'].dt.date]).size().reset_index()
    daily_counts.columns = ['DISTRICT', 'DATE', 'COUNT']
    
    return daily_counts
