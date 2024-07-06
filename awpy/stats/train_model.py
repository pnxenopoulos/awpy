import os
import pandas as pd
import numpy as np
from typing import List
from awpy import Demo
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import log_loss, brier_score_loss
import joblib
from concurrent.futures import ProcessPoolExecutor
import gc
from awpy.stats.win_prob import build_feature_matrix

def process_demo(demo_path: str) -> tuple:
    demo = Demo(file=demo_path)
    
    X_list = []
    y_list = []
    
    for round_num, round_data in demo.rounds.iterrows():
        round_ticks = demo.ticks[demo.ticks['round'] == round_num]['tick'].unique()
        if len(round_ticks) > 0:
            X_round = build_feature_matrix(demo, round_ticks)
            X_round['round'] = round_num
            X_list.append(X_round)
            y_list.extend([round_data['winner'] == 'CT'] * len(round_ticks))
    
    X = pd.concat(X_list, ignore_index=True)
    y = np.array(y_list)
    
    del demo
    gc.collect()
    
    return X, y

def process_demo_batch(demo_paths: List[str]) -> tuple:
    """Process a batch of demos"""
    X_list = []
    y_list = []
    
    for demo_path in demo_paths:
        X, y = process_demo(demo_path)
        X_list.append(X)
        y_list.append(y)
    
    X_batch = pd.concat(X_list)
    y_batch = np.concatenate(y_list)
    
    return X_batch, y_batch

def train_model(X: pd.DataFrame, y: np.ndarray) -> RandomForestClassifier:
    """Train the Random Forest model"""
    # Identify categorical and numerical columns
    categorical_features = ['map_name']
    numerical_features = [col for col in X.columns if col not in categorical_features]

    # Create preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numerical_features),
            ('cat', OneHotEncoder(drop='first', sparse_output=False), categorical_features)
        ])

    # Create a pipeline with the preprocessor and the model
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1))
    ])

    # Fit the pipeline
    model.fit(X, y)
    return model

def main():
    demo_folder = "demos"
    demo_paths = [os.path.join(demo_folder, f) for f in os.listdir(demo_folder) if f.endswith('.dem')]
    
    batch_size = 5  # Process 5 demos at a time
    num_workers = os.cpu_count() - 1  # Use all but one CPU core
    
    X_all = []
    y_all = []
    
    # Process demos in parallel batches
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for i in range(0, len(demo_paths), batch_size):
            batch = demo_paths[i:i+batch_size]
            X_batch, y_batch = executor.submit(process_demo_batch, batch).result()
            
            X_all.append(X_batch)
            y_all.append(y_batch)
            
            # Save intermediate results
            pd.concat(X_all).to_csv(f'X_intermediate_{i}.csv', index=False)
            np.save(f'y_intermediate_{i}.npy', np.concatenate(y_all))
            
            print(f"Processed {i+batch_size} demos")
    
    # Combine all results
    X = pd.concat(X_all, ignore_index=True)
    y = np.concatenate(y_all)
    
    # Train and save the model
    model = train_model(X, y)
    joblib.dump(model, 'wpa_model_rf.joblib')
    
    print("Model training complete")

if __name__ == "__main__":
    main()