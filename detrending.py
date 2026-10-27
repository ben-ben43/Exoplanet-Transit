import numpy as np
import pandas as pd

def rolling_median_filter(time, flux, window_days=2.0, protect_transits=True):
    """
    Calculates a slow-moving baseline trend using a true time-aware rolling median.
    Automatically accounts for observational gaps in the time series.
    Optionally applies an iterative transit protection step to avoid eating into transit dips.
    """
    # Create a time-indexed pandas Series
    time_delta_index = pd.to_timedelta(time, unit='D')
    series = pd.Series(flux, index=time_delta_index)
    window_delta = pd.Timedelta(days=window_days)
    
    # Initial baseline trend calculation
    trend = series.rolling(window_delta, center=True, min_periods=1).median().values
    
    if protect_transits:
        # Identify and temporarily mask deep negative dips (> 3 sigma below trend)
        residuals = flux / trend - 1.0
        mad = np.median(np.abs(residuals - np.median(residuals)))
        sigma = mad * 1.4826 if mad > 0 else np.std(residuals)
        
        # Mask points that are in-transit (> 3 sigma below baseline)
        non_transit_mask = residuals > (-3.0 * sigma)
        
        if np.sum(non_transit_mask) > len(flux) * 0.5:
            # Recompute trend using only out-of-transit stellar baseline
            masked_flux = pd.Series(np.where(non_transit_mask, flux, np.nan), index=time_delta_index)
            # Interpolate masked in-transit values across the baseline
            interpolated_flux = masked_flux.interpolate(method='time').bfill().ffill()
            trend = interpolated_flux.rolling(window_delta, center=True, min_periods=1).median().values

    # Handle any edge NaNs if present
    trend = np.nan_to_num(trend, nan=np.median(flux))
    flattened_flux = flux / trend
    
    return flattened_flux, trend

def run_detrending(time, clean_flux, window_days=2.0):
    """
    Executes the Phase 2 detrending pipeline.
    """
    print("[*] Launching Phase 2: Detrending & Stellar Filtering...")
    print(f"[*] Applying time-aware rolling median filter (Window: {window_days} days)...")
    
    flattened_flux, trend_curve = rolling_median_filter(time, clean_flux, window_days=window_days)
    
    scatter = np.std(flattened_flux) * 1e6
    print("[+] Detrending complete.")
    print(f"[+] Post-detrending residual scatter: {scatter:.2f} ppm")
    
    return flattened_flux, trend_curve