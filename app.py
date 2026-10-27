import os
import sys
import numpy as np
import pandas as pd
import joblib
from flask import Flask, render_template, request, jsonify
from astroquery.mast import Observations

# Import pipeline components
from ingestion import run_pipeline, load_kepler_data, remove_nan_gaps, sigma_clip_cosmic_rays
from detrending import run_detrending
from period_search import find_optimal_period
from folding import run_folding
from feature_extraction import extract_features

app = Flask(__name__, static_folder='static', template_folder='templates')

MODEL_PATH = os.path.join("ml_dataset", "exoplanet_rf_model.joblib")
LABELS_PATH = os.path.join("ml_dataset", "labels.csv")

def downsample_series(x, y, max_points=1200):
    """
    Downsamples time-series data for high-performance frontend rendering
    while preserving min/max extreme features (e.g. sharp transit dips).
    """
    if len(x) <= max_points:
        return x.tolist(), y.tolist()
        
    step = int(np.ceil(len(x) / max_points))
    sampled_indices = np.arange(0, len(x), step)
    return x[sampled_indices].tolist(), y[sampled_indices].tolist()

def get_available_targets():
    """
    Retrieves the list of locally cached and cataloged Kepler targets.
    """
    targets = []
    if os.path.exists(LABELS_PATH):
        df = pd.read_csv(LABELS_PATH)
        for _, row in df.iterrows():
            exists = os.path.exists(row['file_path'])
            targets.append({
                "kic_id": str(row['kic_id']),
                "name": str(row['name']),
                "label": int(row['label']),
                "file_path": str(row['file_path']),
                "cached": exists
            })
            
    # Also search for any stray FITS in mastDownload not in labels.csv
    if os.path.exists("mastDownload"):
        for root, dirs, files in os.walk("mastDownload"):
            for f in files:
                if f.endswith(".fits") and "_llc" in f:
                    full_p = os.path.join(root, f)
                    if not any(t['file_path'] == full_p for t in targets):
                        kic_guess = f.split('-')[0] if '-' in f else "Custom"
                        targets.append({
                            "kic_id": kic_guess,
                            "name": f"Downloaded File ({f})",
                            "label": -1,
                            "file_path": full_p,
                            "cached": True
                        })
    return targets

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/targets', methods=['GET'])
def list_targets():
    try:
        targets = get_available_targets()
        return jsonify({"status": "success", "targets": targets})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/model_info', methods=['GET'])
def model_info():
    if not os.path.exists(MODEL_PATH):
        return jsonify({"status": "not_trained", "message": "Model not trained yet."})
        
    try:
        payload = joblib.load(MODEL_PATH)
        model = payload["model"]
        features = payload["features"]
        importances = model.feature_importances_.tolist()
        
        feature_importance_list = [
            {"feature": feat, "importance": round(imp * 100, 2)} 
            for feat, imp in sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
        ]
        
        return jsonify({
            "status": "ready",
            "feature_importances": feature_importance_list,
            "n_estimators": model.n_estimators,
            "classes": ["False Positive / Binary", "Confirmed Exoplanet"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json or {}
    file_path = data.get('file_path')
    kic_id = data.get('kic_id')
    window_days = float(data.get('window_days', 2.0))
    min_period = float(data.get('min_period', 0.5))
    max_period_input = data.get('max_period')
    max_period = float(max_period_input) if max_period_input is not None and float(max_period_input) > 0 else None
    
    if not file_path or not os.path.exists(file_path):
        # Try to find by kic_id
        if kic_id:
            targets = get_available_targets()
            match = next((t for t in targets if t['kic_id'] == kic_id and t['cached']), None)
            if match:
                file_path = match['file_path']
                
    if not file_path or not os.path.exists(file_path):
        return jsonify({"status": "error", "message": f"FITS file not found: {file_path}"}), 404
        
    try:
        # 1. Pipeline: Ingestion & Quality Filtering
        time, clean_flux = run_pipeline(file_path)
        
        # 2. Pipeline: Detrending
        flattened_flux, trend_curve = run_detrending(time, clean_flux, window_days=window_days)
        
        # 3. Pipeline: BLS Period Search
        best_period, best_t0, bls_results = find_optimal_period(
            time, flattened_flux, min_period=min_period, max_period=max_period
        )
        
        # 4. Pipeline: Phase Folding
        folded_phase, folded_flux = run_folding(time, flattened_flux, best_period, best_t0)
        
        # 5. Pipeline: Diagnostic Feature Extraction
        features = extract_features(folded_phase, folded_flux, bls_results, time=time, flattened_flux=flattened_flux)
        
        # 6. ML Inference
        ml_verdict = None
        probabilities = [0.5, 0.5]
        if os.path.exists(MODEL_PATH):
            payload = joblib.load(MODEL_PATH)
            model = payload["model"]
            feature_names = payload["features"]
            
            feat_df = pd.DataFrame([[features[f] for f in feature_names]], columns=feature_names)
            pred = int(model.predict(feat_df)[0])
            prob = model.predict_proba(feat_df)[0].tolist()
            probabilities = prob
            confidence = round(prob[pred] * 100.0, 1)
            
            ml_verdict = {
                "prediction": pred,
                "label": "CONFIRMED EXOPLANET CANDIDATE" if pred == 1 else "FALSE POSITIVE / BINARY",
                "confidence": confidence,
                "prob_false_positive": round(prob[0] * 100.0, 1),
                "prob_exoplanet": round(prob[1] * 100.0, 1)
            }
            
        # Sample BLS spectrum (e.g. top 1000 points) for charting
        bls_periods, bls_powers = downsample_series(bls_results.period, bls_results.power, max_points=1000)
        
        # Downsample time-series for frontend performance
        raw_time_s, raw_flux_s = downsample_series(time, clean_flux, max_points=1200)
        flat_time_s, flat_flux_s = downsample_series(time, flattened_flux, max_points=1200)
        trend_time_s, trend_curve_s = downsample_series(time, trend_curve, max_points=1200)
        fold_phase_s, fold_flux_s = downsample_series(folded_phase, folded_flux, max_points=1500)
        
        return jsonify({
            "status": "success",
            "best_period": round(float(best_period), 5),
            "best_t0": round(float(best_t0), 5),
            "transit_depth_pct": round(float(features['depth']) * 100.0, 3),
            "features": features,
            "ml_verdict": ml_verdict,
            "charts": {
                "raw": {"time": raw_time_s, "flux": raw_flux_s},
                "detrended": {"time": flat_time_s, "flux": flat_flux_s, "trend": trend_curve_s},
                "bls": {"periods": bls_periods, "powers": bls_powers, "peak_period": float(best_period), "peak_power": float(np.max(bls_results.power))},
                "folded": {"phase": fold_phase_s, "flux": fold_flux_s}
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/download_target', methods=['POST'])
def download_target():
    data = request.json or {}
    kic_id = str(data.get('kic_id', '')).strip()
    if not kic_id:
        return jsonify({"status": "error", "message": "KIC ID is required"}), 400
        
    if not kic_id.startswith("kplr") and kic_id.isdigit():
        kic_id = f"kplr{int(kic_id):09d}"
        
    try:
        obs_table = Observations.query_criteria(target_name=kic_id, obs_collection="Kepler")
        products = Observations.get_product_list(obs_table)
        llc_products = Observations.filter_products(products, productSubGroupDescription="LLC")
        
        if len(llc_products) == 0:
            return jsonify({"status": "error", "message": f"No Long Cadence FITS files found for {kic_id}"}), 404
            
        manifest = Observations.download_products(llc_products[0])
        if manifest is not None and len(manifest) > 0:
            local_path = manifest['Local Path'][0]
            return jsonify({
                "status": "success",
                "message": f"Downloaded {kic_id} successfully",
                "kic_id": kic_id,
                "file_path": local_path
            })
        else:
            return jsonify({"status": "error", "message": "Failed downloading file from MAST."}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"[*] Starting ExoPlanetTransit Web Dashboard on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
