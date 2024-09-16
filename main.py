from flask import Flask, render_template, request, jsonify
import requests
import folium
from geopy.geocoders import Nominatim
import json
import os
import threading
import time
import webbrowser

app = Flask(__name__)

API_KEY = "enter-your-API-token-here"
API_URL = "https://api.openrouteservice.org/v2/isochrones/driving-car"

def geocode_address(address):
    geolocator = Nominatim(user_agent="drive_time_map")
    location = geolocator.geocode(address)
    if location:
        return [location.longitude, location.latitude]
    else:
        raise ValueError("Could not geocode the address. Please check the address and try again.")

def calculate_isochrone(coordinates, time_limit):
    body = {
        "locations": [coordinates],
        "range": [time_limit * 60]
    }

    headers = {
        'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        'Authorization': API_KEY,
        'Content-Type': 'application/json; charset=utf-8'
    }

    try:
        response = requests.post(API_URL, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error: {str(e)}")
        if response:
            print(f"Response content: {response.text}")
        return None

def create_map(center, isochrone):
    m = folium.Map(location=center[::-1], zoom_start=10)
    folium.Marker(center[::-1], popup="Start").add_to(m)
    
    if isochrone and 'features' in isochrone:
        for feature in isochrone['features']:
            if feature['geometry']['type'] == 'Polygon':
                coords = feature['geometry']['coordinates'][0]
                folium.Polygon(
                    locations=[(c[1], c[0]) for c in coords],
                    color="blue",
                    weight=2,
                    fill=True,
                    fill_color="blue",
                    fill_opacity=0.2
                ).add_to(m)
    
    return m

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        address = request.form['address']
        time_limit = float(request.form['time_limit'])
        
        original_time_limit = time_limit
        if time_limit > 60:
            time_limit = 60
        
        try:
            coordinates = geocode_address(address)
            isochrone = calculate_isochrone(coordinates, time_limit)
            
            if isochrone:
                m = create_map(coordinates, isochrone)
                map_html = m.get_root().render()
                
                message = None
                if original_time_limit > 60:
                    message = f"Note: Time limit is restricted to an hour, you entered {int(original_time_limit)} minutes."
                
                return render_template('result.html', map_html=map_html, message=message)
            else:
                return render_template('index.html', error="Failed to calculate the isochrone. Please try again.")
        except Exception as e:
            return render_template('index.html', error=str(e))
    
    return render_template('index.html')

def open_browser():
    """
    Opens the web browser to the Flask app after a short delay, but only once.
    """
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Thread(target=open_browser).start()

    app.run(debug=True, host='0.0.0.0', port=5000)
