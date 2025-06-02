import os
import time
import json
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS 
import paho.mqtt.client as mqtt

# --- Flask App Setup ---
app = Flask(__name__, static_folder='static')
CORS(app) 

# --- Configuration ---
RECEIVED_IMAGE_PATH = "received_photo.jpg" 
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
# Topic for signaling server.py
MQTT_SIGNAL_TOPIC = "image/ready_signal"

# --- MQTT Client for Publishing Signals ---
mqtt_publisher_client = mqtt.Client()

def on_connect_publisher(client, userdata, flags, rc):
    if rc == 0:
        print(f"ImageReceiver (Publisher): Connected to MQTT broker successfully.")
    else:
        print(f"ImageReceiver (Publisher): Failed to connect to MQTT broker, return code {rc}")

def on_disconnect_publisher(client, userdata, rc):
    print(f"ImageReceiver (Publisher): Disconnected with result code {rc}.")

mqtt_publisher_client.on_connect = on_connect_publisher
mqtt_publisher_client.on_disconnect = on_disconnect_publisher

try:
    mqtt_publisher_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_publisher_client.loop_start() 
except Exception as e:
    print(f"ImageReceiver (Publisher): Error connecting to MQTT broker: {e}")

# --- Flask Routes ---

@app.route('/')
def serve_index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except FileNotFoundError:
        return "<h1>Error: index.html not found!</h1><p>Please ensure 'index.html' is in the 'static' directory.</p>", 404

@app.route('/upload_image', methods=['POST'])
def upload_image():
    print("\n--- New Upload Request Received ---")
    print(f"Request Headers: {request.headers}")
    print(f"Request Form Data: {request.form}") # Will now be empty if only 'image' is sent
    print(f"Request Files: {request.files}") 

    if 'image' not in request.files:
        print("Error: 'image' file part not found in request. Missing 'image' field in FormData.")
        return jsonify({"error": "No image file part"}), 400

    file = request.files['image']
    if file.filename == '':
        print("Error: No selected image file in the 'image' part.")
        return jsonify({"error": "No selected image file"}), 400

    if file:
        # We are no longer receiving GPS data via form. Relying purely on EXIF on server.py
        
        if os.path.exists(RECEIVED_IMAGE_PATH):
            try:
                os.remove(RECEIVED_IMAGE_PATH)
                print(f"ImageReceiver (HTTP Server): Deleted previous image '{RECEIVED_IMAGE_PATH}'.")
            except OSError as e:
                print(f"ImageReceiver (HTTP Server): Error deleting previous image '{RECEIVED_IMAGE_PATH}': {e}")
        
        try:
            file.save(RECEIVED_IMAGE_PATH)
            print(f"ImageReceiver (HTTP Server): Image saved to {RECEIVED_IMAGE_PATH}")

            # Signal server.py via MQTT - only send image_path now
            signal_payload_data = {
                "image_path": RECEIVED_IMAGE_PATH
                # No 'gps_data' field in the signal payload
            }
            mqtt_publisher_client.publish(MQTT_SIGNAL_TOPIC, json.dumps(signal_payload_data).encode("utf-8"), qos=1) 
            print(f"ImageReceiver (HTTP Server): Published MQTT signal to {MQTT_SIGNAL_TOPIC} with payload: {signal_payload_data}")

            return jsonify({"message": f"Image received and saved. Signal sent for {RECEIVED_IMAGE_PATH}"}), 200
        
        except Exception as e:
            print(f"ImageReceiver (HTTP Server): Critical error during image saving or signal publishing: {e}")
            return jsonify({"error": f"Failed to process image: {e}"}), 500
    
    return jsonify({"error": "An unexpected error occurred during file upload."}), 500

# --- Main Execution Block ---
# --- Main Execution Block ---
if __name__ == '__main__':
    PORT_TO_USE = 3000
    
    if not os.path.exists('static'):
        os.makedirs('static')
        print("Created 'static' directory. Please place your index.html inside it.")
    
    print(f"\n--- Flask Server Starting ---")
    print(f"Server is listening on: http://0.0.0.0:{PORT_TO_USE}/")
    print(f"Access from YOUR LAPTOP'S BROWSER: http://127.0.0.1:{PORT_TO_USE}/")
    print(f"Access from YOUR IPHONE'S BROWSER: http://<YOUR_LAPTOP_ACTUAL_IP>:{PORT_TO_USE}/") # Replace <YOUR_LAPTOP_ACTUAL_IP>
    print(f"Image upload endpoint: http://<YOUR_LAPTOP_ACTUAL_IP>:{PORT_TO_USE}/upload_image (POST only)") # Replace <YOUR_LAPTOP_ACTUAL_IP>
    print(f"Publishing MQTT signals to: {MQTT_SIGNAL_TOPIC}")
    print(f"--- Server Logs Will Appear Below ---")

    app.run(host='0.0.0.0', port=PORT_TO_USE, debug=False)