import numpy as np

def phase_fold_data(time, flux, period, t0):
    """
    Folds a time-series light curve on a specific period and reference epoch.
    Centers the primary transit dip at phase 0.0.
    """
    # Calculate the fractional phase using the modulo operator
    # This ensures the transit dip appears exactly in the middle of our plot at 0.0
    phase = ((time - t0) / period) % 1.0
    
    # Shift phases > 0.5 to be negative so the plot centers smoothly around 0
    phase[phase > 0.5] -= 1.0
    
    # The folding process scrambles the chronological order of the points.
    # We must sort the arrays by phase so we can plot them smoothly later.
    sort_indices = np.argsort(phase)
    
    folded_phase = phase[sort_indices]
    folded_flux = flux[sort_indices]
    
    return folded_phase, folded_flux

def run_folding(time, flattened_flux, period, t0):
    """
    Executes the folding phase using known or calculated orbital parameters.
    """
    print(f"[*] Launching Phase 3: Phase Folding...")
    print(f"[*] Folding on Period: {period:.5f} days, Epoch (T0): {t0:.5f}")
    
    folded_phase, folded_flux = phase_fold_data(time, flattened_flux, period, t0)
    
    print(f"[+] Data successfully folded. Array shape: {folded_phase.shape}")
    return folded_phase, folded_flux