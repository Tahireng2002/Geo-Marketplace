 
import requests
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def geocode_address(address):
    if not address or not address.strip():
        return None, None, None
    
    try:
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': current_app.config.get('GEOCODING_USER_AGENT', 'geo-marketplace/1.0')
        }
        
        response = requests.get(
            current_app.config.get('GEOCODING_URL', 'https://nominatim.openstreetmap.org/search'),
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]['lat'])
                lng = float(data[0]['lon'])
                formatted = data[0].get('display_name', address)
                return lat, lng, formatted
        
        return None, None, None
        
    except Exception as e:
        logger.error(f"Geocoding error: {str(e)}")
        return None, None, None


def calculate_distance(lat1, lng1, lat2, lng2):
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c