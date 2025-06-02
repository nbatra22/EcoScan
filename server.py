import io
from kindwise import PlantApi
from checkNative import performCompute
from PIL import Image
import piexif
import sys
import time
import os
import json # Import json for parsing the MQTT signal payload
import paho.mqtt.client as mqtt # server.py will now have its own MQTT client

PLANT_ID_API_KEY = "EkQrEcZnThtEeIYk3PF9JmDPOP46u58NnIX0yqeQxE23EEAOtc"

# --- Configuration (shared with image_receiver_http.py) ---
RECEIVED_IMAGE_PATH = "received_photo.jpg" 
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_SIGNAL_TOPIC = "image/ready_signal"

# Global variable to store information from the new image signal
new_image_info = None # Will be a dictionary like {'image_path': '...'}

# --- Hardcoded Fallback GPS Coordinates ---
# These coordinates are for Riverside, CA.
DEFAULT_FALLBACK_GPS = (33.98408888888889, -117.32471388888888) 

def initAPI():
    try:
      api = PlantApi(api_key=PLANT_ID_API_KEY)
      return api
    except ValueError as e:
      print(f"Error initializing PlantApi: {e}")
      print("Please ensure your API key is correctly provided.")
      return None

def plantID(api, image_path, gpsCoord):
    plant_names = []

    try:
        with open(image_path, 'rb') as image_file:
            pass
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}. Ensure image_receiver_http.py saved it there.")
        return []

    print(f"Identifying plant in {image_path}...")

    try:
        identification = api.identify(
            image_path,
            details=['gbif_id'])

        if identification.result.is_plant.binary:
            print("\n--- Plant Detected! ---")
            print(f"Is plant: {identification.result.is_plant.probability:.2%}")

            if identification.result.classification and identification.result.classification.suggestions:
                print("\n--- Top Plant Suggestions: ---")
                for i, suggestion in enumerate(identification.result.classification.suggestions):
                    probability = suggestion.probability * 100
                    gbif_id = suggestion.details.get('gbif_id')
                    print(f"\n{i+1}. Name: {suggestion.name}")
                    print(f"   Probability: {suggestion.probability:.2%}%")
                    print(f"   GBIF ID: {gbif_id}")

                    if probability >= 5.5:
                        plant_names.append({
                            'name':suggestion.name, 
                            'id': gbif_id,
                            'gps': gpsCoord,
                            'native': False})
            else:
                print("No specific plant suggestions found.")

        else:
            print("\n--- No plant detected in the image. ---")
            print(f"Is plant probability: {identification.result.is_plant.probability:.2%}")
            return []

    except Exception as e:
        print(f"An error occurred during identification: {e}")
        return []
    
    return plant_names

def get_decimal_from_dms(dms, ref):
    degrees, minutes, seconds = dms
    decimal = degrees[0] / degrees[1] + \
              minutes[0] / minutes[1] / 60 + \
              seconds[0] / seconds[1] / 3600
    if ref in ['S', 'W']:
        decimal = -decimal
    return decimal

def extract_gps(image_path):
    try:
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get('exif', b''))

        gps_data = exif_dict.get('GPS', {})
        if not gps_data:
            print(f"No GPS data found in EXIF for {image_path}")
            return None

        gps_latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
        gps_latitude_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef)
        gps_longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
        gps_longitude_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef)

        if not all([gps_latitude, gps_latitude_ref, gps_longitude, gps_longitude_ref]):
            print(f"Incomplete GPS data in EXIF for {image_path}")
            return None

        lat = get_decimal_from_dms(gps_latitude, gps_latitude_ref.decode())
        lon = get_decimal_from_dms(gps_longitude, gps_longitude_ref.decode())

        return (lat, lon)
    except Exception as e:
        print(f"Error extracting GPS from EXIF for {image_path}: {e}")
        return None
    
server_mqtt_client = mqtt.Client()


def on_connect_server(client, userdata, flags, rc, ):
    print(f"Server (Subscriber): Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_SIGNAL_TOPIC, qos=1) 

def on_message_server(client, userdata, msg):
    global new_image_info
    if msg.topic == MQTT_SIGNAL_TOPIC:
        try:
            payload = json.loads(msg.payload.decode())
            new_image_info = payload 
            print(f"Server (Subscriber): Received new image signal: {payload}")
        except json.JSONDecodeError as e:
            print(f"Server (Subscriber): Error decoding signal payload: {e}")
        except Exception as e:
            print(f"Server (Subscriber): Unexpected error in signal message: {e}")

server_mqtt_client.on_connect = on_connect_server
server_mqtt_client.on_message = on_message_server

def start_server_mqtt_client():
    try:
        server_mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        server_mqtt_client.loop_start() 
        print("Server (Subscriber): MQTT client started in background, listening for image signals.")
    except Exception as e:
        print(f"Server (Subscriber): Failed to connect to MQTT broker: {e}")

# --- End MQTT client for server.py ---

if __name__ == "__main__":
    api = initAPI()
    if api is None:
        sys.exit("Failed to initialize PlantApi. Exiting.")

    start_server_mqtt_client()
    print("server.py is running and waiting for new image signals from image_receiver_http.py...")

    while True:
        if new_image_info: 
            current_image_path = new_image_info.get('image_path', RECEIVED_IMAGE_PATH)
            
            new_image_info = None 

            print(f"\n--- **New image signal received for '{current_image_path}'. Processing...** ---")
            
            # --- GPS COORDINATE DETERMINATION LOGIC ---
            coords = None # Initialize coords to None

            # 1. Try to extract GPS from EXIF data first
            exif_coords = extract_gps(current_image_path)
            if exif_coords:
                coords = exif_coords
                print(f"Using GPS from EXIF: {coords}")
            else:
                print(f"No GPS data found in EXIF for {current_image_path}.")
                
                # 2. If EXIF GPS is not available, use the hardcoded default
                coords = DEFAULT_FALLBACK_GPS
                print(f"Using HARDCODED DEFAULT GPS: {coords}")
            # --- END GPS COORDINATE DETERMINATION LOGIC ---

            if coords: # Coords will always be available now due to fallback
                plantNames = plantID(api, current_image_path, coords)
                
                print("\n--- Identified Plants: ---")
                print(plantNames)

                if plantNames:
                    print("\n--- Checking nativeness for each plant ---")
                    for plant_info in plantNames:
                        plant_id = plant_info['id']
                        plant_gps = plant_info['gps']
                        
                        print(f"\nProcessing: {plant_info['name']} (ID: {plant_id}) at {plant_info['gps']}")
                        try:
                            plant_info['native'] = performCompute(plant_gps, plant_id)
                        except Exception as e:
                            print(f"Error during performCompute for {plant_info['name']}: {e}")
                    
                    print("\n--- After performCompute for each plant ---")
                    print(plantNames)
                else:
                    print("No plants identified or processed for nativeness.")
            else:
                # This 'else' branch should theoretically never be reached now,
                # as coords will always be set to either EXIF or DEFAULT_FALLBACK_GPS.
                print("Skipping plant identification due to missing GPS coordinates (should not happen with fallback).")

        time.sleep(1) 

    server_mqtt_client.loop_stop()
    server_mqtt_client.disconnect()