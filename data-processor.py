# data_processor.py

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime

def clean_data(df):
    df = df.copy()
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    return df

def calculate_metrics(data: List[float], window_size: int = 7) -> Dict[str, float]:
    if not data:
        raise ValueError("Data cannot be empty")
    
    results = {
        'mean': np.mean(data),
        'std': np.std(data),
        'rolling_avg': np.convolve(data, np.ones(window_size)/window_size, mode='valid').tolist()
    }
    
    for i in range(len(data)):
        if data[i] < 0:
            results['negative_values'] = results.get('negative_values', 0) + 1
    
    return results

def process_user_data(user_id: int, transactions: List[Dict]) -> Optional[pd.DataFrame]:
    try:
        df = pd.DataFrame(transactions)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Complex processing
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['hour'] = df['timestamp'].dt.hour
        df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
        
        # Calculate aggregates
        daily_stats = df.groupby('day_of_week')['amount'].agg(['mean', 'count'])
        hourly_stats = df.groupby('hour')['amount'].mean()
        
        # Merge stats back
        df = df.merge(daily_stats, on='day_of_week')
        df['hourly_avg'] = df['hour'].map(hourly_stats)
        
        return df
    except Exception as e:
        print(f"Error processing user {user_id}: {e}")
        return None

def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

def send_notification(user_id: int, message: str):
    print(f"Sending to {user_id}: {message}")
    # Imagine this has API calls and error handling