import folium
import numpy as np
import requests
import polyline

def get_osrm_route(coords_sequence):
    """Fetches a route from OSRM based on a sequence of coordinates."""
    # OSRM takes coordinates as (longitude, latitude)
    waypoints = [f"{lon},{lat}" for lat, lon in coords_sequence]
    coords_str = ";".join(waypoints)
    url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}"
    params = {"overview": "full", "geometries": "polyline"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        route_polyline = data['routes'][0]['geometry']
        return polyline.decode(route_polyline)
    except requests.exceptions.RequestException as e:
        print(f"\nWarning: Could not fetch OSRM route. Using straight lines. Error: {e}")
        return None

def create_route_map(path, city_coords, city_danger_scores):
    """Creates an advanced Folium map with color-coded nodes and an OSRM route."""
    if not path:
        print("No path found to display.")
        return None

    avg_lat = np.mean([city_coords[loc][0] for loc in path])
    avg_lon = np.mean([city_coords[loc][1] for loc in path])
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

    # Add all city nodes with danger-based colors
    for area, coord in city_coords.items():
        score = city_danger_scores.get(area, 0)
        if score < 3.5: color = "green"
        elif score < 6: color = "orange"
        else: color = "red"
        
        folium.CircleMarker(
            location=coord, radius=5,
            popup=f"{area}<br>Danger Score: {score:.2f}",
            color=color, fill=True, fill_opacity=0.7
        ).add_to(m)

    # Add prominent Start and End markers
    folium.Marker(location=city_coords[path[0]], popup=f"START: {path[0]}", icon=folium.Icon(color='green', icon='play')).add_to(m)
    folium.Marker(location=city_coords[path[-1]], popup=f"END: {path[-1]}", icon=folium.Icon(color='red', icon='stop')).add_to(m)

    # Get and plot the actual road route from OSRM
    path_coords = [city_coords[loc] for loc in path]
    osrm_route_geometry = get_osrm_route(path_coords)
    
    if osrm_route_geometry:
        # If OSRM call is successful, draw the detailed route
        folium.PolyLine(
            osrm_route_geometry, color='blue', weight=5, opacity=0.8
        ).add_to(m)
    else:
        # Fallback to straight lines if OSRM fails
        folium.PolyLine(path_coords, color='purple', weight=3, opacity=0.8).add_to(m)

    return m

def save_map(map_object, filename="safest_route.html"):
    """Saves a Folium map object to an HTML file."""
    if map_object:
        map_object.save(filename)
        print(f"\n🗺️ Success! Your route map has been saved to {filename}")