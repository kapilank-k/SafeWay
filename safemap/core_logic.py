import numpy as np
import networkx as nx
import heapq
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from math import radians, sin, cos, sqrt, atan2
import pandas as pd # Make sure pandas is imported here too

def calculate_danger_scores(data_df):
    """
    Calculates a weighted danger score for each area based on crime and lighting.
    """
    crime_counts = data_df.groupby(['city', 'area_name']).size().reset_index(name='crime_count')
    area_features = data_df.groupby(['city', 'area_name']).agg({
        'lighting_quality_score': 'mean',
        'uptime_ratio': 'mean'
    }).reset_index()
    processed_data = pd.merge(crime_counts, area_features, on=['city', 'area_name'])

    def normalize(series):
        if series.max() == series.min():
            return pd.Series(0, index=series.index)
        return (series - series.min()) / (series.max() - series.min())

    processed_data['crime_norm'] = processed_data.groupby('city')['crime_count'].transform(normalize)
    processed_data['lighting_inverted_norm'] = 1 - processed_data.groupby('city')['lighting_quality_score'].transform(normalize)
    crime_weight = 0.7
    lighting_weight = 0.3
    processed_data['danger_score'] = (crime_weight * processed_data['crime_norm']) + (lighting_weight * processed_data['lighting_inverted_norm'])
    processed_data['danger_score'] = 1 + 9 * normalize(processed_data['danger_score'])
    return processed_data

def geocode_areas(data_df):
    """
    Adds latitude and longitude coordinates for each area using geocoding.
    """
    geolocator = Nominatim(user_agent="safemap_application_v1.0")
    coordinates = {}
    unique_areas = data_df[['city', 'area_name']].drop_duplicates()

    print("Starting geocoding process... This may take a while depending on the number of unique areas.")
    for index, row in unique_areas.iterrows():
        city, area = row['city'], row['area_name']
        query = f"{area}, {city}, India"
        try:
            location = geolocator.geocode(query, timeout=10)
            coords = (location.latitude, location.longitude) if location else None
            coordinates[(city, area)] = coords
            print(f"  Geocoded: {query} -> {coords}")
            time.sleep(1)
        except (GeocoderTimedOut, GeocoderUnavailable):
            print(f"  Service timed out for {query}. Retrying with longer delay...")
            time.sleep(5)
            try:
                location = geolocator.geocode(query, timeout=15)
                coords = (location.latitude, location.longitude) if location else None
                coordinates[(city, area)] = coords
                print(f"  Retry success: {query} -> {coords}")
            except Exception as e:
                print(f"  Could not geocode {query} after retry: {e}")
                coordinates[(city, area)] = None
        except Exception as e:
            print(f"  An unexpected error occurred for {query}: {e}")
            coordinates[(city, area)] = None

    data_df['coords'] = data_df.apply(lambda r: coordinates.get((r['city'], r['area_name'])), axis=1)
    data_df.dropna(subset=['coords'], inplace=True)
    print("\nGeocoding complete.")
    return data_df

def haversine_distance(coord1, coord2):
    """Calculate the distance between two lat/lon points in kilometers."""
    R = 6371.0 # Earth radius in kilometers
    
    lat1, lon1 = map(radians, coord1)
    lat2, lon2 = map(radians, coord2)
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

def a_star_search(graph, start_node, end_node, coords_map, danger_scores):
    """
    Finds the safest path from a start to an end node using the A* algorithm.
    The cost function g(n) is the cumulative danger score.
    The heuristic h(n) is the haversine distance.
    """
    open_set = []
    # Heap stores (f_score, g_score, node)
    heapq.heappush(open_set, (0, 0, start_node))

    came_from = {}
    g_score = {node: float('inf') for node in graph.nodes}
    g_score[start_node] = 0

    f_score = {node: float('inf') for node in graph.nodes}
    f_score[start_node] = haversine_distance(coords_map[start_node], coords_map[end_node])

    while open_set:
        _, current_g, current_node = heapq.heappop(open_set)

        if current_node == end_node:
            path = []
            while current_node in came_from:
                path.append(current_node)
                current_node = came_from[current_node]
            path.append(start_node)
            return path[::-1] # Return the reversed path

        for neighbor in graph.neighbors(current_node):
            # g(n) is the cumulative danger score to reach the neighbor
            tentative_g_score = current_g + danger_scores[neighbor]

            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current_node
                g_score[neighbor] = tentative_g_score
                
                # h(n) is the heuristic distance from the neighbor to the end
                heuristic = haversine_distance(coords_map[neighbor], coords_map[end_node])
                
                # f(n) = g(n) + h(n)
                f_score[neighbor] = tentative_g_score + heuristic
                heapq.heappush(open_set, (f_score[neighbor], tentative_g_score, neighbor))

    return None # Return None if no path is found

def build_city_graphs(processed_data):
    """
    Builds a fully connected graph for each city from the processed data.

    Args:
        processed_data (pd.DataFrame): DataFrame containing geocoded areas
                                       with their danger scores.

    Returns:
        tuple: A tuple containing three dictionaries:
               - city_graphs (dict): {city_name: networkx.Graph}
               - city_coords (dict): {city_name: {area_name: (lat, lon)}}
               - city_danger_scores (dict): {city_name: {area_name: score}}
    """
    city_graphs = {}
    city_coords = {}
    city_danger_scores = {}

    print("\nBuilding city networks...")
    for city in processed_data['city'].unique():
        G = nx.Graph()
        city_df = processed_data[processed_data['city'] == city]
        nodes = city_df['area_name'].tolist()
        G.add_nodes_from(nodes)

        # Create a fully connected graph for each city.
        # This assumes any area is directly reachable from any other area.
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                G.add_edge(nodes[i], nodes[j])

        city_graphs[city] = G
        city_coords[city] = pd.Series(city_df.coords.values, index=city_df.area_name).to_dict()
        city_danger_scores[city] = pd.Series(city_df.danger_score.values, index=city_df.area_name).to_dict()
        print(f"  - Built graph for {city} with {len(nodes)} nodes.")
        
    print("All city graphs have been created.")
    return city_graphs, city_coords, city_danger_scores