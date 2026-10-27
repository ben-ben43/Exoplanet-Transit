import numpy as np
from astropy.io import fits

def load_kepler_data(file_path, filter_quality=True):
    """
    Loads TIME, PDCSAP_FLUX (or SAP_FLUX fallback), and SAP_QUALITY from a Kepler FITS file.
    Optionally applies standard Kepler quality flag filtering (SAP_QUALITY == 0).
    """
    with fits.open(file_path) as hdul:
        data_table = hdul[1].data
        col_names = data_table.columns.names
        
        time = np.array(data_table['TIME'], dtype=np.float64)
        
        # Primary choice is PDC-conditioned flux; fallback to SAP flux if PDC is unavailable or empty
        if 'PDCSAP_FLUX' in col_names and not np.all(np.isnan(data_table['PDCSAP_FLUX'])):
            flux = np.array(data_table['PDCSAP_FLUX'], dtype=np.float64)
        elif 'SAP_FLUX' in col_names:
            flux = np.array(data_table['SAP_FLUX'], dtype=np.float64)
        else:
            raise ValueError(f"No valid flux columns found in {file_path}")
            
        quality = np.array(data_table['SAP_QUALITY'], dtype=np.int32) if 'SAP_QUALITY' in col_names else None

    # Quality flag filtering: quality == 0 denotes optimal cadences with no known flags
    if filter_quality and quality is not None:
        good_mask = (quality == 0)
        time = time[good_mask]
        flux = flux[good_mask]

    return time, flux

def remove_nan_gaps(time, flux):
    """
    Removes NaN or non-positive flux values and corresponding timestamps.
    """
    valid_mask = ~np.isnan(flux) & ~np.isnan(time) & (flux > 0)
    return time[valid_mask], flux[valid_mask]

def sigma_clip_cosmic_rays(time, flux, sigma_threshold=5.0, window_size=51):
    """
    Applies directional sigma-clipping to reject positive cosmic ray spikes.
    Uses a localized rolling median/MAD baseline to prevent clipping legitimate 
    astrophysical stellar variability or starspot peaks.
    """
    n_points = len(flux)
    if n_points < window_size:
        # Fallback to robust global MAD for very small segments
        median_flux = np.median(flux)
        mad = np.median(np.abs(flux - median_flux))
        sigma_equivalent = (mad * 1.4826) if mad > 0 else np.std(flux)
        cutoff = median_flux + (sigma_threshold * sigma_equivalent)
        clean_mask = flux < cutoff
        return time[clean_mask], flux[clean_mask]

    # Ensure window_size is odd
    if window_size % 2 == 0:
        window_size += 1

    # Fast localized windowed median via stride tricks
    pad_w = window_size // 2
    padded_flux = np.pad(flux, pad_w, mode='reflect')
    
    shape = (n_points, window_size)
    strides = (padded_flux.strides[0], padded_flux.strides[0])
    windows = np.lib.stride_tricks.as_strided(padded_flux, shape=shape, strides=strides)
    
    local_median = np.median(windows, axis=1)
    local_mad = np.median(np.abs(windows - local_median[:, np.newaxis]), axis=1)
    local_sigma = np.where(local_mad > 0, local_mad * 1.4826, np.std(flux))
    
    # Positive cosmic-ray rejection only (preserves downward exoplanet transits)
    upper_limit = local_median + (sigma_threshold * local_sigma)
    clean_mask = flux <= upper_limit

    return time[clean_mask], flux[clean_mask]

def run_pipeline(file_path):
    """
    Executes the Phase 1 Ingestion and Telemetry Cleaning Pipeline.
    """
    print(f"[*] Ingesting file: {file_path}")
    raw_time, raw_flux = load_kepler_data(file_path, filter_quality=True)
    print(f"[+] Loaded raw data: {len(raw_time)} cadences.")

    clean_time, clean_flux = remove_nan_gaps(raw_time, raw_flux)
    nan_count = len(raw_time) - len(clean_time)
    print(f"[+] Removed {nan_count} missing/NaN/negative data points.")

    final_time, final_flux = sigma_clip_cosmic_rays(clean_time, clean_flux)
    spike_count = len(clean_time) - len(final_time)
    print(f"[+] Removed {spike_count} cosmic ray spikes.")
    print(f"[+] Phase 1 Complete. Clean arrays ready for detrending: {len(final_time)} cadences.")

    return final_time, final_flux

if __name__ == "__main__":
    pass