import numpy as np
from astropy.timeseries import BoxLeastSquares

def find_optimal_period(time, flattened_flux, min_period=0.5, max_period=None, n_periods=6000):
    """
    Uses the Box-Fitting Least Squares (BLS) algorithm to autonomously 
    search for the optimal orbital period, reference epoch, and transit duration.
    Samples periods uniformly in frequency space for optimal statistical coverage.
    """
    print("[*] Launching Automated Period Search (BLS)...")
    
    # Baseline observation span in days
    total_baseline = time[-1] - time[0]
    
    # Set default max_period to half baseline or 20.0 days (whichever is smaller)
    if max_period is None:
        max_period = min(20.0, max(min_period + 1.0, total_baseline / 2.0))
        
    # Initialize the BLS model with cleaned, flattened data
    model = BoxLeastSquares(time, flattened_flux)
    
    # Uniform frequency grid ensures equal resolution across both short and long orbital periods
    min_freq = 1.0 / max_period
    max_freq = 1.0 / min_period
    frequency_grid = np.linspace(min_freq, max_freq, n_periods)
    period_grid = 1.0 / frequency_grid
    
    # Dynamically scale trial transit durations (from ~30 mins up to ~6 hours)
    durations = np.linspace(0.02, 0.25, 12)
    
    print(f"[*] Scanning {n_periods} periods from {min_period:.2f} to {max_period:.2f} days...")
    results = model.power(period_grid, duration=durations)
    
    # Find peak SNR period
    best_index = np.argmax(results.power)
    
    best_period = results.period[best_index]
    best_t0 = results.transit_time[best_index]
    best_depth = results.depth[best_index]
    best_duration = results.duration[best_index]
    
    print(f"[+] Optimal Period Found: {best_period:.5f} days")
    print(f"[+] Reference Epoch (T0): {best_t0:.5f}")
    print(f"[+] Estimated Transit Depth: {best_depth * 100:.3f}%")
    print(f"[+] Estimated Transit Duration: {best_duration * 24.0:.2f} hours")
    
    return best_period, best_t0, results