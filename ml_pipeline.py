import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Import pipeline stages
from ingestion import run_pipeline
from detrending import run_detrending
from period_search import find_optimal_period
from folding import run_folding
from feature_extraction import extract_features

FEATURE_COLUMNS = [
    'depth', 
    'duration_phase', 
    'baseline_noise', 
    'snr', 
    'secondary_depth_ratio', 
    'odd_even_mismatch', 
    'transit_flatness'
]

def build_feature_dataset(labels_csv_path):
    """
    Loops through the labeled CSV, runs the full processing pipeline on each file, 
    and builds an exoplanet vetting dataset with complete astrophysical features.
    """
    print("[*] Launching Phase 5: Building ML Dataset from Catalog...")
    
    df = pd.read_csv(labels_csv_path)
    features_list = []
    
    for index, row in df.iterrows():
        file_path = row['file_path']
        kic_id = row['kic_id']
        label = row['label']
        name = row['name']
        
        print(f"\n[*] Processing target {name} ({kic_id})...")
        
        if not os.path.exists(file_path):
            print(f"[-] Error: File not found at {file_path}. Skipping.")
            continue
            
        try:
            # 1. Ingestion & Cosmic Ray Cleaning
            time, clean_flux = run_pipeline(file_path)
            
            # 2. Vectorized Detrending
            flattened_flux, _ = run_detrending(time, clean_flux, window_days=2.0)
            
            # 3. Frequency-Uniform BLS Period Search
            best_period, best_t0, bls_results = find_optimal_period(time, flattened_flux)
            
            # 4. Phase Fold
            folded_phase, folded_flux = run_folding(time, flattened_flux, best_period, best_t0)
            
            # 5. Extract Diagnostic Features (including Odd-Even & Secondary Eclipse)
            features = extract_features(
                folded_phase, 
                folded_flux, 
                bls_results, 
                time=time, 
                flattened_flux=flattened_flux
            )
            
            features['kic_id'] = kic_id
            features['name'] = name
            features['label'] = int(label)
            
            features_list.append(features)
            
        except Exception as e:
            print(f"[-] Failed processing {kic_id}: {e}")
            
    features_df = pd.DataFrame(features_list)
    print(f"\n[+] Feature Extraction Complete. Processed {len(features_df)} targets successfully.")
    
    # Save extracted features table for fast reloading
    output_features_csv = os.path.join("ml_dataset", "extracted_features.csv")
    features_df.to_csv(output_features_csv, index=False)
    print(f"[+] Saved extracted features table to {output_features_csv}")
    
    return features_df

def train_exoplanet_classifier(features_df, model_save_path=None):
    """
    Trains a Random Forest classifier using Stratified K-Fold cross validation
    and serializes the trained model to disk for standalone inference.
    """
    print("\n[*] Training Random Forest Classifier on Astrophysical Features...")
    
    X = features_df[FEATURE_COLUMNS]
    y = features_df['label'].astype(int)
    
    # Count samples per class
    class_counts = y.value_counts().to_dict()
    print(f"[*] Class Distribution: {class_counts} (0: False Positive/Binary, 1: Exoplanet)")
    min_class = min(class_counts.values())
    
    # Perform Stratified K-Fold Cross Validation if sample count allows
    n_splits = min(5, min_class)
    if n_splits >= 2:
        print(f"[*] Running {n_splits}-Fold Stratified Cross Validation...")
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        
        cv_results = cross_validate(
            RandomForestClassifier(n_estimators=100, random_state=42),
            X, y,
            cv=skf,
            scoring=['accuracy', 'precision', 'recall', 'f1']
        )
        
        print("\n--- Cross-Validation Performance (Mean +/- Std) ---")
        print(f"Accuracy:  {np.mean(cv_results['test_accuracy']) * 100:.1f}% (+/- {np.std(cv_results['test_accuracy']) * 100:.1f}%)")
        print(f"Precision: {np.mean(cv_results['test_precision']) * 100:.1f}% (+/- {np.std(cv_results['test_precision']) * 100:.1f}%)")
        print(f"Recall:    {np.mean(cv_results['test_recall']) * 100:.1f}% (+/- {np.std(cv_results['test_recall']) * 100:.1f}%)")
        print(f"F1-Score:  {np.mean(cv_results['test_f1']):.3f} (+/- {np.std(cv_results['test_f1']):.3f})")
        print("---------------------------------------------------")
    else:
        print("[!] Too few samples per class for K-Fold CV; training directly on full set.")

    # Train final production model on all available benchmark data
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X, y)
    
    # Feature Importance analysis
    importances = rf_model.feature_importances_
    feat_ranking = sorted(zip(FEATURE_COLUMNS, importances), key=lambda x: x[1], reverse=True)
    print("\n[*] Feature Importance Rankings:")
    for feat, imp in feat_ranking:
        print(f"  {feat:25s}: {imp * 100:5.2f}%")
        
    # Serialize model to disk
    if model_save_path is None:
        model_save_path = os.path.join("ml_dataset", "exoplanet_rf_model.joblib")
        
    model_payload = {
        "model": rf_model,
        "features": FEATURE_COLUMNS
    }
    joblib.dump(model_payload, model_save_path)
    print(f"\n[+] Trained model saved successfully to: {model_save_path}")
    
    return rf_model

if __name__ == "__main__":
    csv_path = os.path.join("ml_dataset", "labels.csv")
    
    if os.path.exists(csv_path):
        dataset = build_feature_dataset(csv_path)
        if len(dataset) >= 4:
            model = train_exoplanet_classifier(dataset)
        else:
            print("[-] Not enough data to train the model. Ensure batch_downloader.py downloaded targets.")
    else:
        print(f"[-] Could not find labels CSV at {csv_path}. Run batch_downloader.py first.")