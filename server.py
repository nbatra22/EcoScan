import io
from kindwise import PlantApi
from checkNative import performCompute
from PIL import Image
import piexif
import sys

PLANT_ID_API_KEY = ""  # replace with Plant.id API key
IMAGE_PATH = "" # replace with image path
def initAPI():
    try:
      api = PlantApi(api_key=PLANT_ID_API_KEY)
      return api
    except ValueError as e:
      print(f"Error initializing PlantApi: {e}")
      print("Please ensure your API key is correctly provided.")
      return None
      exit()

def plantID(api, gpsCoord):
    
    plant_names = []

    try:
        with open(IMAGE_PATH, 'rb') as image_file:
            pass
    except FileNotFoundError:
        print(f"Error: Image file not found")
        return []

    print(f"Identifying plant in {IMAGE_PATH}...")

    try:
        identification = api.identify(
            IMAGE_PATH,
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
                    print(f"   Probability: {suggestion.probability:.2%}")
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
    plantNames = plantID(api, coords)
    
    print(plantNames)

    print("\n--- Checking nativeness for each plant ---")
    for plant_info in plantNames:
        plant_id = plant_info['id']
        plant_gps = plant_info['gps']
        
        print(f"\nProcessing: {plant_info['name']} (ID: {plant_id}) at {plant_info['gps']}")
        plant_info['native'] = performCompute(plant_gps, plant_id)
    
    print("\n--- After performCompute for each plant ---")
    print(plantNames)