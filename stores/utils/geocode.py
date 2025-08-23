import requests
from django.conf import settings

def get_coords_from_address(address: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": settings.GOOGLE_GEOCODING_API_KEY,
        "language": "ko"
    }
    resp = requests.get(url, params=params).json()

    # 👇 디버깅용 출력
    print(f"[Geocode Request] {address}")
    print(f"[Geocode Response] {resp}")

    if resp.get("status") != "OK" or not resp.get("results"):
        return None, None

    location = resp["results"][0]["geometry"]["location"]
    return float(location["lat"]), float(location["lng"])
