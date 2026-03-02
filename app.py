import requests
import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
from flask import Flask, send_from_directory, render_template_string
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

def fetch_hurricanes():
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("activeStorms", [])
    return []

def fetch_disaster_news():
    url = "https://api.bing.microsoft.com/v7.0/news/search"
    headers = {"Ocp-Apim-Subscription-Key":"YOUR_BING_API_KEY"}  # Replace with your Bing API key
    params = {"q":"earthquake OR wildfire OR hurricane OR flood OR volcano OR tsunami","count":5,"mkt":"en-US"}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 200:
        articles = r.json().get("value", [])
        return pd.DataFrame([{
            "Headline":a.get("name"),
            "Source":a.get("provider")[0]["name"] if a.get("provider") else "Unknown",
            "Published":a.get("datePublished"),
            "URL":a.get("url")
        } for a in articles])
    return pd.DataFrame()

# === Map Generators ===
def visualize_disasters(earthquakes, wildfires, hurricanes):
    m = folium.Map(location=[20,0], zoom_start=2)
    for eq in earthquakes[:20]:
        coords = eq["geometry"]["coordinates"]
        folium.CircleMarker(
            location=[coords[1],coords[0]],
            radius=6,
            popup=f"M {eq['properties']['mag']} - {eq['properties']['place']}",
            color="red", fill=True, fill_color="red"
        ).add_to(m)
    for _,row in wildfires.head(20).iterrows():
        folium.Marker(
            location=[row["latitude"],row["longitude"]],
            popup=f"🔥 Wildfire: Brightness {row['brightness']} on {row['acq_date']} {row['acq_time']}",
            icon=folium.Icon(color="orange",icon="fire",prefix="fa")
        ).add_to(m)
    m.save("disasters_map.html")

def visualize_disasters_with_time(earthquakes, wildfires):
    features=[]
    for eq in earthquakes[:20]:
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
    for _,row in wildfires.head(20).iterrows():
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
    <h2>Real-Time Multi-Disaster Dashboard</h2>
    <ul>
      <li><a href="/map">Static Map</a></li>
      <li><a href="/time">Animated Map</a></li>
      <li><a href="/data">Disaster Data</a></li>
    </ul>
    """

@app.route("/map")
def serve_static_map():
    return send_from_directory(os.getcwd(),"disasters_map.htdeml")

@app.route("/time")
def serve_time_map():
    return send_from_directory(os.getcwd(),"disasters_time_map.html")

@app.route("/data")
def show_data():
    eqs = fetch_earthquakes()
    wfs = fetch_wildfires()
    hcs = fetch_hurricanes()
    news = fetch_disaster_news()

    eq_table = pd.DataFrame([{"Magnitude":eq["properties"]["mag"],"Location":eq["properties"]["place"]} for eq in eqs[:10]]).to_html(classes="table table-striped", index=False) if eqs else "<p>No significant earthquakes found in the past 24h.</p>"
    wf_table = wfs.head(10).to_html(classes="table table-striped", index=False) if not wfs.empty else "<p>No major wildfires detected in the past 48h.</p>"
    hc_table = pd.DataFrame(hcs).to_html(classes="table table-striped", index=False) if hcs else "<p>No active hurricanes</p>"
    news_table = news.to_html(classes="table table-striped", index=False) if not news.empty else "<p>No news headlines available</p>"

    html = f"""
    <h2>Disaster Data Dashboard</h2>
    <h3>Earthquakes</h3>{eq_table}
    <h3>Wildfires</h3>{wf_table}
    <h3>Hurricanes</h3>{hc_table}
    <h3>News Headlines</h3>{news_table}
    """
    return render_template_string(html)

# === Main ===
def main():
    print("=== Real-Time Multi-Disaster Dashboard ===\n")

    earthquakes = fetch_earthquakes()
    wildfires = fetch_wildfires()
    hurricanes = fetch_hurricanes()

    print("=== Significant Earthquakes (Past 24h, M≥4.5) ===")
    for eq in earthquakes[:10]:
        print(eq["properties"]["mag"], "-", eq["properties"]["place"])

    print("\n=== Major Wildfires (Past 48h, Brightness≥320) ===")
    print(wildfires.head(10))

    print("\n=== Hurricanes/Cyclones ===")
    if hurricanes:
        for storm in hurricanes:
            print(storm.get("stormName"), "-", storm.get("stormType"))
    else:
        print("No active hurricanes/cyclones at the moment.")

    news = fetch_disaster_news()
    print("\n=== Disaster News Headlines ===")
    print(news)

    # Generate both maps
    visualize_disasters(earthquakes, wildfires, hurricanes)
    visualize_disasters_with_time(earthquakes, wildfires)

    # Final console messages
    print("\nStatic map saved as disasters_map.html — open it in your browser to view.")
    print("Animated map saved as disasters_time_map.html — open it in your browser to view.")

    # Start Flask server
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
