import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return None

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371.0
    return round(c * r, 1)

PRESET_LOCATIONS = {
    'kolhapur': {'name': 'Kolhapur', 'lat': 16.6956, 'lon': 74.2317},
    'london': {'name': 'London', 'lat': 51.5074, 'lon': -0.1278},
    'pune': {'name': 'Pune', 'lat': 18.5204, 'lon': 73.8567},
    'mumbai': {'name': 'Mumbai', 'lat': 19.0760, 'lon': 72.8777},
}
