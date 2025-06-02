import requests
import json

TEST_PLANT_ID = '3172371'
TEST_GEO_COORDINATES = (33.97559444444445, -117.3256611111111)
OPENCAGE_API_KEY = "10891d1c87204fc1b9e8608144525938" #replace with opencage id

TDWG_MAP = {
    "US-CA": "TDWG:CAL", 
    "CA-AB" : "TDWG:ABT" }

def get_iso3166(latitude, longitude, api_key):

    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": f"{latitude},{longitude}",
        "key": api_key,
    }

    print(f"Making request to OpenCage for: ({latitude}, {longitude})...")
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status() 
        data = response.json()

        if data and data['results']:
            components = data['results'][0]['components']

            # get the ISO_3166-2 code 
            if 'ISO_3166-2' in components and isinstance(components['ISO_3166-2'], dict):
                for key in components['ISO_3166-2']:
                    iso_code = components['ISO_3166-2'][key]
                    if '-' in iso_code and iso_code.startswith(components.get('country_code', '').upper()):
                        return iso_code.upper()
                    
                # if loop finishes without ISO_3166-2, try other paths
            
            country_code = components.get('country_code', '').upper()
            if 'state_code' in components and country_code:
                return f"{country_code}-{components['state_code'].upper()}"
            if 'province_code' in components and country_code:
                return f"{country_code}-{components['province_code'].upper()}"

            print("Warning: ISO_3166-2 code for subdivision not found in OpenCage response.")
            return None
        else:
            print("No results found for the given coordinates.")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        print("Please check your API key and coordinates.")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None
def iso2tdwg (iso_code):

    if iso_code in TDWG_MAP:
        print(f"Map Code: {TDWG_MAP[iso_code]}")
        return TDWG_MAP[iso_code]
            
    print(f"Warning: No TDWG code found in map for {iso_code}")
    return None

def checkNative(gbif_id, tdwg_id):

    gbif_distributions_url = f"https://api.gbif.org/v1/species/{gbif_id}/distributions"
    print(f"\nMaking request to GBIF for species {gbif_id} distributions...")
    try:
        response = requests.get(gbif_distributions_url)
        response.raise_for_status() 
        distributions_data = response.json()

        if not distributions_data or not distributions_data.get('results'):
            print(f"No distribution data found for species ID {gbif_id}.")
            return None 

        for dist in distributions_data['results']:
            
            if not tdwg_id.startswith("TDWG:"):
                tdwg_id = f"TDWG:{tdwg_id}"

            if dist.get('locationId') == tdwg_id:
                establishment_means = dist.get('establishmentMeans')
                if establishment_means is None or establishment_means in ['NATIVE', 'ENDEMIC']:
                    print(f"Species {gbif_id} is found and is considered NATIVE in {tdwg_id}.")
                    return True
                elif establishment_means in ['INTRODUCED', 'INVASIVE', 'NATURALIZED']:
                    print(f"Species {gbif_id} is found and is considered {establishment_means} in {tdwg_id}.")
                    return False
                else:
                    print(f"Species {gbif_id} found in {tdwg_id}, but establishmentMeans is '{establishment_means}' (status unclear).")
                    return None 
        
        print(f"Species {gbif_id} distribution record for {tdwg_id} not found.")
        return False # not present means not native based on GBIF data for that specific region

    except requests.exceptions.HTTPError as e:
        print(f"GBIF API HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"GBIF API Connection Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during GBIF API call: {e}")
    return None

def performCompute(geoCoord, plantID):

  iso_code = get_iso3166(
      geoCoord[0],
      geoCoord[1],
      OPENCAGE_API_KEY
  )
  if iso_code:
      print(f"\nSuccessfully extracted ISO_3166-2 code: {iso_code}")
      tdwgCode = iso2tdwg(iso_code)

      if tdwgCode:
          is_native = checkNative(plantID, tdwgCode)

          if is_native is True:
              print(f"\nFinal Result: Plant {plantID} is likely NATIVE at {geoCoord}.")
              return True
          elif is_native is False:
              print(f"\nFinal Result: Plant {plantID} is NOT NATIVE at {geoCoord}.")
          else:
              print(f"\nFinal Result: Could not determine nativeness for Plant {plantID} at {geoCoord}.")
      else:
          print("Cannot proceed: No TDWG ID found for the given ISO_3166-2 code.")
  else:
      print("\nFailed to extract ISO_3166-2 code.")

  return False