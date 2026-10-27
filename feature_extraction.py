import numpy as np

def extract_features(folded_phase, folded_flux, bls_results, time=None, flattened_flux=None):
    """
    Extracts geometric, statistical, and astrophysical vetting features from the transit light curve.
    Includes Odd-Even transit comparison, Secondary Eclipse checks, and Transit Shape flatness
    to reliably distinguish Exoplanets from False Positives (e.g. Eclipsing Binaries).
    """
    print("\n[*] Launching Phase 4: Astrophysical Feature Extraction...")
    
    best_idx = np.argmax(bls_results.power)
    transit_depth = float(bls_results.depth[best_idx])
    transit_duration_days = float(bls_results.duration[best_idx])
    best_period = float(bls_results.period[best_idx])
    best_t0 = float(bls_results.transit_time[best_idx])
    
    # 1. Normalized Transit Duration (Duty Cycle)
    transit_duration_phase = transit_duration_days / best_period
    half_dur = transit_duration_phase / 2.0
    
    # 2. In-Transit vs Out-of-Transit Masks
    in_transit_mask = np.abs(folded_phase) <= half_dur
    out_of_transit_mask = np.abs(folded_phase) > (half_dur + 0.02)
    
    baseline_flux = folded_flux[out_of_transit_mask] if np.sum(out_of_transit_mask) > 0 else folded_flux
    baseline_noise = float(np.std(baseline_flux))
    
    # 3. Robust SNR
    n_in_transit = np.sum(in_transit_mask)
    if baseline_noise > 0 and n_in_transit > 0:
        snr = float((transit_depth / baseline_noise) * np.sqrt(n_in_transit))
    else:
        snr = 0.0

    # 4. Secondary Eclipse Search (at Phase ~ 0.5)
    # Exoplanet secondary eclipses are tiny (< 100 ppm); binary secondary stars produce noticeable dips
    secondary_mask = (np.abs(folded_phase) >= 0.45) & (np.abs(folded_phase) <= 0.55)
    if np.sum(secondary_mask) > 2:
        secondary_flux = folded_flux[secondary_mask]
        secondary_depth = float(max(0.0, 1.0 - np.median(secondary_flux)))
        secondary_depth_ratio = float(secondary_depth / transit_depth) if transit_depth > 0 else 0.0
    else:
        secondary_depth = 0.0
        secondary_depth_ratio = 0.0

    # 5. Transit Shape / Flatness Index (U-shape vs V-shape)
    # Measures the ratio of core transit depth (inner 40%) to outer ingress/egress depth
    inner_mask = np.abs(folded_phase) <= (half_dur * 0.4)
    outer_mask = (np.abs(folded_phase) > (half_dur * 0.4)) & (np.abs(folded_phase) <= half_dur)
    
    if np.sum(inner_mask) > 0 and np.sum(outer_mask) > 0:
        inner_depth = 1.0 - np.median(folded_flux[inner_mask])
        outer_depth = 1.0 - np.median(folded_flux[outer_mask])
        transit_flatness = float(inner_depth / max(outer_depth, 1e-6))
    else:
        transit_flatness = 1.0

    # 6. Odd vs Even Transit Depth Comparison
    # Primary diagnostic for Eclipsing Binaries: alternating eclipses have mismatched depths
    odd_even_mismatch = 0.0
    if time is not None and flattened_flux is not None and best_period > 0:
        # Calculate transit epoch index for each point
        cycle_numbers = np.round((time - best_t0) / best_period)
        transit_phases = ((time - best_t0) / best_period) - cycle_numbers
        
        in_transit_points = np.abs(transit_phases) <= half_dur
        
        odd_mask = in_transit_points & ((cycle_numbers % 2).astype(int) != 0)
        even_mask = in_transit_points & ((cycle_numbers % 2).astype(int) == 0)
        
        if np.sum(odd_mask) > 2 and np.sum(even_mask) > 2:
            odd_depth = max(0.0, 1.0 - np.median(flattened_flux[odd_mask]))
            even_depth = max(0.0, 1.0 - np.median(flattened_flux[even_mask]))
            max_d = max(odd_depth, even_depth, 1e-6)
            odd_even_mismatch = float(abs(odd_depth - even_depth) / max_d)

    # Package clean, normalized feature vector
    features = {
        "depth": transit_depth,
        "duration_phase": transit_duration_phase,
        "baseline_noise": baseline_noise,
        "snr": snr,
        "secondary_depth_ratio": secondary_depth_ratio,
        "odd_even_mismatch": odd_even_mismatch,
        "transit_flatness": transit_flatness
    }
    
    print("--- Exoplanet Diagnostic Feature Report ---")
    print(f"  Transit Depth:        {features['depth']*100:.3f}%")
    print(f"  Duration Phase:       {features['duration_phase']:.4f} of orbit")
    print(f"  Baseline Noise:       {features['baseline_noise']*1e6:.1f} ppm")
    print(f"  Transit SNR:          {features['snr']:.1f}")
    print(f"  Secondary / Primary:  {features['secondary_depth_ratio']*100:.2f}%")
    print(f"  Odd-Even Mismatch:    {features['odd_even_mismatch']*100:.2f}%")
    print(f"  Transit Flatness:     {features['transit_flatness']:.2f}")
    print("-------------------------------------------\n")
    
    return features