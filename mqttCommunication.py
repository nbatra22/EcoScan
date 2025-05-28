import paho.mqtt.client as mqtt
import base64

photo_chunks = {}
gps_data = None

def on_connect(client, userdata, flags, rc):
    print("Connected:", rc)
    client.subscribe("iphone/gps")
    client.subscribe("iphone/photo")
    client.subscribe("iphone/photo-done")

def on_message(client, userdata, msg):
    global gps_data
    topic = msg.topic
    payload = msg.payload.decode()

    if topic == "iphone/gps":
        gps_data = payload
        print("GPS:", gps_data)

    elif topic == "iphone/photo":
        data = eval(payload)  # {index, chunk}
        photo_chunks[int(data['index'])] = data['chunk']

    elif topic == "iphone/photo-done":
        # Reconstruct image
        ordered = [photo_chunks[i] for i in sorted(photo_chunks)]
        with open("received_photo.jpg", "wb") as f:
            f.write(base64.b64decode("".join(ordered)))
        print("Image saved as received_photo.jpg")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("test.mosquitto.org", 1883, 60)
client.loop_forever()
