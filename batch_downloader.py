import os
import csv
from astroquery.mast import Observations

# Expanded benchmark dataset of confirmed Kepler exoplanets & eclipsing binary false positives
TARGETS = {
    # Confirmed Exoplanets (Class 1)
    "kplr011446443": {"label": 1, "name": "TrES-2b / Kepler-1b (Hot Jupiter)"},
    "kplr010666592": {"label": 1, "name": "HAT-P-7b / Kepler-2b (Hot Jupiter)"},
    "kplr011904151": {"label": 1, "name": "Kepler-4b (Sub-Neptune)"},
    "kplr008191672": {"label": 1, "name": "Kepler-5b (Hot Jupiter)"},
    "kplr010874614": {"label": 1, "name": "Kepler-6b (Hot Jupiter)"},
    "kplr005780885": {"label": 1, "name": "Kepler-7b (Hot Jupiter)"},
    "kplr006922244": {"label": 1, "name": "Kepler-8b (Hot Jupiter)"},
    "kplr011395645": {"label": 1, "name": "Kepler-10b (Rocky Planet)"},
    "kplr005812701": {"label": 1, "name": "Kepler-12b (Hot Jupiter)"},
    
    # Eclipsing Binaries / Astrophysical False Positives (Class 0)
    "kplr003230227": {"label": 0, "name": "Eclipsing Binary (KIC 3230227)"},
    "kplr004139816": {"label": 0, "name": "Eclipsing Binary (KIC 4139816)"},
    "kplr005617259": {"label": 0, "name": "Eclipsing Binary (KIC 5617259)"},
    "kplr008145465": {"label": 0, "name": "Eclipsing Binary (KIC 8145465)"},
    "kplr009117492": {"label": 0, "name": "Eclipsing Binary (KIC 9117492)"},
    "kplr006289257": {"label": 0, "name": "Eclipsing Binary (KIC 6289257)"},
    "kplr006889235": {"label": 0, "name": "Eclipsing Binary (KIC 6889235)"},
    "kplr008552719": {"label": 0, "name": "Eclipsing Binary (KIC 8552719)"},
    "kplr009651063": {"label": 0, "name": "Eclipsing Binary (KIC 9651063)"}
}

def download_mini_dataset():
    """
    Downloads Long Cadence (LLC) FITS files for each target in the catalogue.
    Skips files that are already cached locally in the mastDownload directory.
    Saves an updated labels.csv mapping files to metadata and labels.
    """
    print("[*] Beginning Batch Download for Exoplanet ML Dataset...")
    
    os.makedirs("ml_dataset", exist_ok=True)
    csv_path = os.path.join("ml_dataset", "labels.csv")
    
    logged_rows = []
    
    for kic_id, info in TARGETS.items():
        print(f"\n[*] Target: {info['name']} ({kic_id})...")
        
        # Check if already present on disk in mastDownload
        existing_file = None
        for root, dirs, files in os.walk("mastDownload"):
            for f in files:
                if kic_id in f and f.endswith(".fits") and "_llc" in f:
                    existing_file = os.path.join(root, f)
                    break
            if existing_file:
                break
                
        if existing_file and os.path.exists(existing_file):
            print(f"[+] Found cached FITS file: {existing_file}")
            logged_rows.append([existing_file, kic_id, info["label"], info["name"]])
            continue
            
        try:
            # Query MAST
            obs_table = Observations.query_criteria(target_name=kic_id, obs_collection="Kepler")
            products = Observations.get_product_list(obs_table)
            llc_products = Observations.filter_products(products, productSubGroupDescription="LLC")
            
            if len(llc_products) == 0:
                print(f"[-] No LLC data found for {kic_id}. Skipping.")
                continue
                
            print(f"[*] Downloading Quarter 1 for {kic_id}...")
            manifest = Observations.download_products(llc_products[0])
            
            if manifest is not None and len(manifest) > 0:
                local_path = manifest['Local Path'][0]
                logged_rows.append([local_path, kic_id, info["label"], info["name"]])
                print(f"[+] Downloaded and logged {kic_id}")
        except Exception as e:
            print(f"[-] Error retrieving {kic_id}: {e}")

    # Write updated CSV
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["file_path", "kic_id", "label", "name"])
        for row in logged_rows:
            writer.writerow(row)

    print(f"\n[+] Batch catalog complete! {len(logged_rows)} targets saved to {csv_path}")

if __name__ == "__main__":
    download_mini_dataset()