import paho.mqtt.client as mqtt
import base64
import time
import os # Import os for file operations

photo_chunks = {}
gps_data = None

# Define a fixed path where the received image will be saved
RECEIVED_IMAGE_PATH = "received_photo.jpg"
# A flag to indicate if a new image has been received and saved
new_image_received = False

def on_connect(client, userdata, flags, rc):
    print("Connected:", rc)
    client.subscribe("iphone/gps")
    client.subscribe("iphone/photo")
    client.subscribe("iphone/photo-done")

def on_message(client, userdata, msg):
    global gps_data, new_image_received
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == "iphone/gps":
        gps_data = payload
        print("GPS:", gps_data)

    elif topic == "iphone/photo":
        data = eval(payload)  # {index, chunk}
        
        # If this is the first chunk of a new photo, prepare for it
        if int(data['index']) == 0:
            # Check if the photo path already exists and delete it
            if os.path.exists(RECEIVED_IMAGE_PATH):
                try:
                    os.remove(RECEIVED_IMAGE_PATH)
                    print(f"**Previous image '{RECEIVED_IMAGE_PATH}' deleted before receiving new photo.**")
                except OSError as e:
                    print(f"Error deleting previous image '{RECEIVED_IMAGE_PATH}': {e}")
            photo_chunks.clear() # Clear any old chunks
            new_image_received = False # Reset flag for new photo

        photo_chunks[int(data['index'])] = data['chunk']
        print(f"**Receiving image chunk {data['index']}...**")

    elif topic == "iphone/photo-done":
        # Reconstruct image
        ordered = [photo_chunks[i] for i in sorted(photo_chunks)]
        with open(RECEIVED_IMAGE_PATH, "wb") as f:
            f.write(base64.b64decode("".join(ordered)))
        print(f"**Image saved as {RECEIVED_IMAGE_PATH}**")
        new_image_received = True # Set the flag
        # Clear chunks for next image
        photo_chunks.clear()
    
    new_image_received = True

# Initialize MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def start_mqtt_client():
    try:
        client.connect("test.mosquitto.org", 1883, 60)
        client.loop_start() # Use loop_start to run in background
        print("MQTT client started in background.")
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")

def get_received_image_path():
    return RECEIVED_IMAGE_PATH

def get_gps_data():
    return gps_data

def is_new_image_received():
    global new_image_received
    if new_image_received:
        new_image_received = False # Reset the flag after checking
        return True
    return False

if __name__ == "__main__":
    start_mqtt_client()
    try:
        while True:
            time.sleep(1) # Keep the main thread alive to allow MQTT loop to run
    except KeyboardInterrupt:
        print("Stopping MQTT client.")
        client.loop_stop()
        client.disconnect()