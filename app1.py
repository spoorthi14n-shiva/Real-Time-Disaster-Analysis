# app1.py

import requests
import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
from flask import Flask, send_from_directory
from io import StringIO
import os

app = Flask(__name__)

# === Data Fetchers ===
def fetch_earthquakes():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        return [eq for eq in data["features"] if eq["properties"]["mag"] and eq["properties"]["mag"] >= 4.5]
    return []

def fetch_wildfires():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_48h.csv"
    r = requests.get(url)
    if r.status_code == 200:
        df = pd.read_csv(StringIO(r.text))
        return df[df["brightness"] >= 320][["latitude","longitude","brightness","acq_date","acq_time"]]
    return pd.DataFrame()

# === Map Generators ===
def generate_maps():
    eqs = fetch_earthquakes()
    wfs = fetch_wildfires()

    # Static map
    m = folium.Map(location=[20,0], zoom_start=2)
    for eq in eqs[:20]:
        coords = eq["geometry"]["coordinates"]
        folium.CircleMarker(
            location=[coords[1],coords[0]],
            radius=6,
            popup=f"M {eq['properties']['mag']} - {eq['properties']['place']}",
            color="red", fill=True, fill_color="red"
        ).add_to(m)
    for _,row in wfs.head(20).iterrows():
        folium.Marker(
            location=[row["latitude"],row["longitude"]],
            popup=f"🔥 Wildfire: Brightness {row['brightness']} on {row['acq_date']} {row['acq_time']}",
            icon=folium.Icon(color="orange",icon="fire",prefix="fa")
        ).add_to(m)
    m.save("disasters_map.html")

    # Animated map
    features=[]
    for eq in eqs[:20]:
        coords=eq["geometry"]["coordinates"]
        time=eq["properties"]["time"]
        features.append({
            "type":"Feature",
            "geometry":{"type":"Point","coordinates":[coords[0],coords[1]]},
            "properties":{
                "time":pd.to_datetime(time,unit="ms").isoformat(),
                "popup":f"🌍 Earthquake: M {eq['properties']['mag']} - {eq['properties']['place']}",
                "icon":"circle",
                "iconstyle":{"color":"red","fillColor":"red","fillOpacity":0.6}
            }
        })
    for _,row in wfs.head(20).iterrows():
        features.append({
            "type":"Feature",
            "geometry":{"type":"Point","coordinates":[row["longitude"],row["latitude"]]},
            "properties":{
                "time":pd.to_datetime(row["acq_date"],errors="coerce").isoformat(),
                "popup":f"🔥 Wildfire: Brightness {row['brightness']} on {row['acq_date']} {row['acq_time']}",
                "icon":"circle",
                "iconstyle":{"color":"orange","fillColor":"orange","fillOpacity":0.6}
            }
        })
    m2=folium.Map(location=[20,0],zoom_start=2)
    TimestampedGeoJson({"type":"FeatureCollection","features":features},
                       period="PT1H",add_last_point=True,auto_play=False,loop=False).add_to(m2)
    m2.save("disasters_time_map.html")

# === Flask Routes ===
@app.route("/")
def index():
    return """
    <h2>Real-Time Disaster Dashboard</h2>
    <ul>
      <li><a href="/map">Static Map</a> – Interactive map with basemap layers and disaster markers</li>
      <li><a href="/time">Animated Map</a> – Timeline map showing earthquakes & wildfires over time</li>
    </ul>
    """

@app.route("/map")
def serve_static_map():
    return send_from_directory(os.getcwd(),"disasters_map.html")

@app.route("/time")
def serve_time_map():
    return send_from_directory(os.getcwd(),"disasters_time_map.html")

if __name__=="__main__":
    generate_maps()
    print("\nDashboard running at: http://127.0.0.1:5000")
    print("Static Map: http://127.0.0.1:5000/map – Interactive map with basemap layers and disaster markers")
    print("Animated Map: http://127.0.0.1:5000/time – Timeline map showing earthquakes & wildfires over time")
    app.run(debug=True, use_reloader=False)
