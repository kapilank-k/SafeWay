import sys
import os

# This is the crucial fix that adds your project folder to Python's path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# Now, the rest of your imports will work correctly at runtime
from safemap.data_handler import load_and_combine_data
from safemap.core_logic import (
    calculate_danger_scores,
    geocode_areas,
    build_city_graphs,
    a_star_search
)
from safemap.visualization import create_route_map, save_map

DATA_FILE_PATH = 'data/SafeMap_dataset.xlsx'

def run_application():
    """The main function to run the SafeMap application."""
    print("Starting SafeMap...")
    
    # --- Data Processing Pipeline ---
    combined_data = load_and_combine_data(DATA_FILE_PATH)
    if combined_data is None:
        print("\nFailed to load data. Exiting application.")
        return

    print("\nCalculating danger scores...")
    processed_data = calculate_danger_scores(combined_data)
    
    geocoded_data = geocode_areas(processed_data)
    if geocoded_data is None or geocoded_data.empty:
        print("\nGeocoding failed. Cannot proceed.")
        return

    graphs, coords, dangers = build_city_graphs(geocoded_data)
    
    print("\nSetup complete. Ready to find the safest route.")
    
    # --- User Interaction ---
    try:
        # Get city from user
        available_cities = list(graphs.keys())
        print(f"\nAvailable cities: {', '.join(available_cities)}")
        city = input("Enter the city you want to find a route in: ")
        if city not in available_cities:
            print("Invalid city name. Please restart.")
            return

        # Get start and end points
        print(f"\nAvailable areas in {city}: {', '.join(graphs[city].nodes())}")
        start_area = input("Enter the starting area: ")
        end_area = input("Enter the destination area: ")

        if start_area not in graphs[city].nodes() or end_area not in graphs[city].nodes():
            print("Invalid start or end area. Please restart.")
            return

        # --- Pathfinding and Visualization ---
        print("\nFinding the safest route...")
        path = a_star_search(
            graphs[city],
            start_area,
            end_area,
            coords[city],
            dangers[city]
        )
        
        if path:
            print(f"Path found: {' -> '.join(path)}")
            route_map = create_route_map(path, coords[city], dangers[city])
            save_map(route_map)
        else:
            print("No path could be found between the specified locations.")
            
    except KeyboardInterrupt:
        print("\nApplication exited by user.")

if __name__ == "__main__":
    run_application()