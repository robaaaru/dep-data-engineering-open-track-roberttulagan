import requests
from pathlib import Path

# This script's own folder, no matter where you run it from
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # creates data/raw if it doesn't exist

output_path = OUTPUT_DIR / "IBTrACS_WP_2020_2026.csv"

url = (
    "https://erddap.aoml.noaa.gov/hdb/erddap/tabledap/IBTrACS_since1980_1.csv"
    "?sid,season,name,time,latitude,longitude,wmo_wind"
    "&basin=%22WP%22"
    "&season>=2020"
    "&season<=2026"
)

print("Downloading filtered IBTrACS data from ERDDAP...")
response = requests.get(url, stream=True, timeout=120)

with open(output_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

print("Done!")