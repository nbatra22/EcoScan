from PIL import Image
import piexif
import sys

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
    if len(sys.argv) != 2:
        print("Usage: python extract_gps.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    coords = extract_gps(image_path)

    if coords:
        print(f"GPS Coordinates: Latitude = {coords[0]}, Longitude = {coords[1]}")
    else:
        print("No GPS data found in image.")
