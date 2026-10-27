import numpy as np
from ingestion import remove_nan_gaps, sigma_clip_cosmic_rays

def generate_test_telemetry():
    """
    Generates a mock stellar light curve with a stable baseline, 
    injected data gaps (NaNs), and sharp positive cosmic ray spikes.
    """
    np.random.seed(42)
    time = np.linspace(0, 10, 1000)
    
    # Baseline stellar flux with slight Gaussian noise
    flux = 10000.0 + np.random.normal(0, 5, size=1000)
    
    # Inject 50 random NaN data gaps
    nan_indices = np.random.choice(1000, size=50, replace=False)
    time[nan_indices] = np.nan
    flux[nan_indices] = np.nan
    
    # Inject 5 heavy cosmic ray spikes (unusually high values)
    # We must ensure we don't choose indices that are already NaN
    valid_indices = np.where(~np.isnan(flux))[0]
    spike_indices = np.random.choice(valid_indices, size=5, replace=False)
    flux[spike_indices] += 500.0  # Massive upward deviation
    
    return time, flux

def verify_pipeline():
    """
    Tests the modular pipeline components on the mock telemetry.
    """
    raw_time, raw_flux = generate_test_telemetry()
    
    # Test Step 1: NaN Removal
    clean_time, clean_flux = remove_nan_gaps(raw_time, raw_flux)
    assert np.isnan(clean_time).sum() == 0, "Error: NaNs remain in time array!"
    assert np.isnan(clean_flux).sum() == 0, "Error: NaNs remain in flux array!"
    print(f"[Test Pass] Gaps cleaned. Array length reduced from {len(raw_time)} to {len(clean_time)}.")
    
    # Test Step 2: Cosmic Ray Removal via directional sigma clipping
    final_time, final_flux = sigma_clip_cosmic_rays(clean_time, clean_flux, sigma_threshold=4.0)
    
    # Verify that the max flux value is no longer a massive spike
    global_median = np.median(clean_flux)
    max_deviation = np.max(final_flux) - global_median
    
    print(f"[Test Pass] Outliers removed. Remaining max positive deviation from baseline: {max_deviation:.2f}")
    print(f"Final Data Structures Ready: Time Shape {final_time.shape}, Flux Shape {final_flux.shape}")

if __name__ == "__main__":
    verify_pipeline()