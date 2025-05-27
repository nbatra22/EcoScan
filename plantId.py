import io
from kindwise import PlantApi
from PIL import Image
import piexif
import sys

    # --- Configuration ---
PLANT_ID_API_KEY = "EJJfz4RfgDhynxuJedPvdC7xz1MXzuZ5OUfl5A277oh2bGnU1P"  # Replace with your actual Plant.id API key
IMAGE_PATH = "plant2.jpg"      # Changed to plant2.jpg as per your output
def initAPI():
    try:
      api = PlantApi(api_key=PLANT_ID_API_KEY)
      return api
    except ValueError as e:
      print(f"Error initializing PlantApi: {e}")
      print("Please ensure your API key is correctly provided.")
      return None
      exit()

def plantID(api):
    plant_names = []

    try:
        with open(IMAGE_PATH, 'rb') as image_file:
            pass
    except FileNotFoundError:
        print(f"Error: Image file not found")
        return []

    print(f"Identifying plant in {IMAGE_PATH}...")

    try:
        identification = api.identify(IMAGE_PATH)

        if identification.result.is_plant.binary:
            print("\n--- Plant Detected! ---")
            print(f"Is plant: {identification.result.is_plant.probability:.2%}")

            if identification.result.classification and identification.result.classification.suggestions:
                print("\n--- Top Plant Suggestions: ---")
                for i, suggestion in enumerate(identification.result.classification.suggestions):
                    probability = suggestion.probability * 100
                    print(f"\n{i+1}. Name: {suggestion.name}")
                    print(f"   Probability: {suggestion.probability:.2%}")

                    if probability >= 5.5:
                        plant_names.append(suggestion.name)
            else:
                print("No specific plant suggestions found.")

        else:
            print("\n--- No plant detected in the image. ---")
            print(f"Is plant probability: {identification.result.is_plant.probability:.2%}")
            return []

    except Exception as e: # Catch errors
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
    img = Image.open(image_path)
    exif_dict = piexif.load(img.info.get('exif', b''))

    gps_data = exif_dict.get('GPS', {})
    if not gps_data:
        return None

    try:
        gps_latitude = gps_data[piexif.GPSIFD.GPSLatitude]
        gps_latitude_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef].decode()
        gps_longitude = gps_data[piexif.GPSIFD.GPSLongitude]
        gps_longitude_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef].decode()

        lat = get_decimal_from_dms(gps_latitude, gps_latitude_ref)
        lon = get_decimal_from_dms(gps_longitude, gps_longitude_ref)

        return (lat, lon)
    except KeyError:
        return None



if __name__ == "__main__":

    coords = extract_gps(IMAGE_PATH)
    api = initAPI()
    plantNames = plantID(api)
    
    print(plantNames)
    print(f"GPS Coordinates: Latitude = {coords[0]}, Longitude = {coords[1]}")