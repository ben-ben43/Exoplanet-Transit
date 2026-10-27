import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from ingestion import run_pipeline
from detrending import run_detrending
from period_search import find_optimal_period
from folding import run_folding
from feature_extraction import extract_features

def classify_candidate(features, model_path=None):
    """
    Loads the trained Random Forest model and performs automated inference on candidate features.
    """
    if model_path is None:
        model_path = os.path.join("ml_dataset", "exoplanet_rf_model.joblib")
        
    if not os.path.exists(model_path):
        print(f"[!] Warning: Trained model not found at {model_path}. Train model first with ml_pipeline.py.")
        return None, None
        
    try:
        saved_payload = joblib.load(model_path)
        model = saved_payload["model"]
        feature_names = saved_payload["features"]
        
        # Prepare single-row DataFrame matching trained feature columns
        feat_vector = pd.DataFrame([[features[f] for f in feature_names]], columns=feature_names)
        
        prediction = model.predict(feat_vector)[0]
        probabilities = model.predict_proba(feat_vector)[0]
        
        label_str = "CONFIRMED EXOPLANET CANDIDATE" if prediction == 1 else "FALSE POSITIVE / BINARY"
        confidence = probabilities[prediction] * 100.0
        
        print("\n=======================================================")
        print(f"[ML] AUTOMATED CLASSIFICATION VERDICT: {label_str}")
        print(f"Confidence: {confidence:.2f}% | Class Probabilities: [FP: {probabilities[0]*100:.1f}%, Planet: {probabilities[1]*100:.1f}%]")
        print("=======================================================\n")
        
        return label_str, confidence
    except Exception as e:
        print(f"[-] Error during ML inference: {e}")
        return None, None

def plot_results(time, raw_flux, flattened_flux, folded_phase, folded_flux, best_period, best_t0, features, ml_verdict=None):
    fig, axs = plt.subplots(3, 1, figsize=(11, 13))
    
    # 1. Cleaned Telemetry
    axs[0].scatter(time, raw_flux, s=3, color='#4A5568', alpha=0.8)
    axs[0].set_title("Phase 1: Kepler Raw Telemetry (Quality-Filtered & De-Spiked)", fontsize=12, fontweight='bold')
    axs[0].set_xlabel("Time (BJD - 2454833)")
    axs[0].set_ylabel("Normalized Flux (e-/s)")
    axs[0].grid(True, linestyle='--', alpha=0.4)
    
    # 2. Detrended Flux
    axs[1].scatter(time, flattened_flux, s=3, color='#2B6CB0', alpha=0.8)
    axs[1].axhline(1.0, color='red', linestyle='--', linewidth=1)
    axs[1].set_title("Phase 2: Stellar Baseline Detrended & Flattened", fontsize=12, fontweight='bold')
    axs[1].set_xlabel("Time (BJD - 2454833)")
    axs[1].set_ylabel("Relative Flux")
    axs[1].grid(True, linestyle='--', alpha=0.4)
    
    # 3. Phase Folded Transit Profile
    axs[2].scatter(folded_phase, folded_flux, s=6, color='#E53E3E', alpha=0.75, label='Cadences')
    axs[2].set_title(f"Phase 3: Phase-Folded Transit (P = {best_period:.4f} d, Epoch = {best_t0:.4f})", fontsize=12, fontweight='bold')
    axs[2].set_xlabel("Orbital Phase (Center = 0.0)")
    axs[2].set_ylabel("Relative Flux")
    axs[2].set_xlim(-0.25, 0.25)
    axs[2].grid(True, linestyle='--', alpha=0.4)
    
    # Text Annotation of Diagnostic Features and ML Verdict
    verdict_text = f"ML Verdict: {ml_verdict[0]} ({ml_verdict[1]:.1f}% conf)" if ml_verdict and ml_verdict[0] else "ML Verdict: Not Loaded"
    info_box = (
        f"{verdict_text}\n"
        f"Depth: {features['depth']*100:.3f}% | SNR: {features['snr']:.1f}\n"
        f"Odd-Even Mismatch: {features['odd_even_mismatch']*100:.1f}%\n"
        f"Sec/Pri Ratio: {features['secondary_depth_ratio']*100:.1f}%"
    )
    axs[2].text(0.02, 0.08, info_box, transform=axs[2].transAxes, fontsize=9,
                verticalalignment='bottom', bbox=dict(boxstyle='round,pad=0.5', facecolor='#EDF2F7', edgecolor='#A0AEC0', alpha=0.9))

    plt.tight_layout()
    plt.savefig("transit_analysis_result.png", dpi=150)
    print("[+] Saved analysis visualization to transit_analysis_result.png")
    # Non-blocking plot display if in GUI
    try:
        plt.show(block=False)
    except Exception:
        pass

def main():
    fits_file = None
    
    # Check if a specific fits file is passed as a command-line argument
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        fits_file = sys.argv[1]
    else:
        # Search for any downloaded FITS file
        for root, dirs, files in os.walk("mastDownload"):
            for file in files:
                if file.endswith(".fits") and "_llc" in file:
                    fits_file = os.path.join(root, file)
                    break
            if fits_file:
                break
                
    if not fits_file:
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".fits") and "_llc" in file:
                    fits_file = os.path.join(root, file)
                    break
            if fits_file:
                break

    if not fits_file:
        print("[-] Error: Could not locate any .fits files. Run download_data.py or batch_downloader.py first.")
        return

    # Execute complete scientific pipeline
    time, clean_flux = run_pipeline(fits_file)
    flattened_flux, trend_curve = run_detrending(time, clean_flux, window_days=2.0)
    
    best_period, best_t0, bls_results = find_optimal_period(time, flattened_flux)
    folded_phase, folded_flux = run_folding(time, flattened_flux, best_period, best_t0)
    
    features = extract_features(folded_phase, folded_flux, bls_results, time=time, flattened_flux=flattened_flux)
    
    # Automated Machine Learning Classification
    ml_verdict = classify_candidate(features)
    
    plot_results(time, clean_flux, flattened_flux, folded_phase, folded_flux, best_period, best_t0, features, ml_verdict)

if __name__ == "__main__":
    main()

