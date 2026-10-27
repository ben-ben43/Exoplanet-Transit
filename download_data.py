from astroquery.mast import Observations

def fetch_kepler_file():
    print("[*] Querying NASA MAST database for KIC 11446443...")
    
    # 1. Search for all observations of our target star
    obs_table = Observations.query_criteria(
        target_name="kplr011446443", 
        obs_collection="Kepler"
    )
    
    # 2. Get the list of all files associated with those observations
    products = Observations.get_product_list(obs_table)
    
    # 3. Filter strictly for Long Cadence (LLC) light curves
    llc_products = Observations.filter_products(
        products, 
        productSubGroupDescription="LLC"
    )
    
    if len(llc_products) == 0:
        print("[-] Error: No LLC files found.")
        return

    print(f"[+] Found {len(llc_products)} Long Cadence files.")
    print("[*] Downloading the first available Quarter...")
    
    # 4. Download just the first file in the list
    manifest = Observations.download_products(llc_products[0])
    
    print(f"\n[+] Success! File downloaded to: {manifest['Local Path'][0]}")

if __name__ == "__main__":
    fetch_kepler_file()