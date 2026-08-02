import requests

url = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv"

print("Downloading IBTrACS Western Pacific typhoon data...")
response = requests.get(url, stream=True, timeout=120)

with open("../data/raw/IBTrACS.WP.v04r01.csv", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

print("Done!")