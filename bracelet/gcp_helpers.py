import datetime
import json
import platform
import ssl
import jwt
import paho.mqtt.client as mqtt
from rfc3339 import rfc3339


# GCP PARAMETERS
ca_certs = "roots.pem"
private_key_file = "rsa_private.pem"
algorithm = "RS256"
message_type = "event"
mqtt_bridge_hostname = "mqtt.googleapis.com"
mqtt_bridge_port = 8883
project_id = "project-m1ia-oct22"
cloud_region = "us-central1"
registry_id = "registre_prenom" # modification : indiquer le nom de votre registre
device_id = "bracelet"


def create_jwt(project_id, private_key_file, algorithm):
    """Creates a JWT (https://jwt.io) to establish an MQTT connection.
      Args:
       project_id: The cloud project ID this device belongs to
       private_key_file: A path to a file containing either an RSA256 or
               ES256 private key.
       algorithm: The encryption algorithm to use. Either 'RS256' or 'ES256'
      Returns:
          An MQTT generated from the given project_id and private key, which
          expires in 20 minutes. After 20 minutes, your client will be
          disconnected, and a new JWT will have to be generated.
      Raises:
          ValueError: If the private_key_file does not contain a known key.
      """
    token = {
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        "aud": project_id
    }
    with open(private_key_file, 'r') as f:
        private_key = f.read()
    print(f"Creating JWT using {algorithm} from private key file {private_key_file}")
    return jwt.encode(token, private_key, algorithm=algorithm)


def get_client(project_id, cloud_region, registry_id, device_id, private_key_file,
               algorithm, ca_certs, mqtt_bridge_hostname, mqtt_bridge_port):
    """Create our MQTT client. The client_id is a unique string that identifies
      this device. For Google Cloud IoT Core, it must be in the format below."""
    client = mqtt.Client(
        client_id=f"projects/{project_id}/locations/{cloud_region}/registries/{registry_id}/devices/{device_id}"
    )
    client.username_pw_set(
        username='unused',
        password=create_jwt(project_id, private_key_file, algorithm)
    )
    client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect(mqtt_bridge_hostname, mqtt_bridge_port)
    mqtt_config_topic = f"/devices/{device_id}/config"
    client.subscribe(mqtt_config_topic, qos=1)
    mqtt_commands_topic = f"/devices/{device_id}/commands/#"
    client.subscribe(mqtt_commands_topic, qos=1)
    client.loop_start()
    return client


def error_str(rc):
    """Convert a Paho error to a human readable string."""
    return f"{rc}: {mqtt.error_string(rc)}"


def on_connect(unused_client, unused_userdata, unused_flags, rc):
    """Callback for when a device connects."""
    print(f"gcp_on_connect {error_str(rc)}")


def on_disconnect(unused_client, unused_userdata, rc):
    """Paho callback for when a device disconnects."""
    print(f"gcp_on_disconnect {error_str(rc)}")


def on_publish(unused_client, unused_userdata, unused_mid):
    """Paho callback when a message is sent to the broker."""
    print("gcp_on_publish")


def on_message(unused_client, unused_userdata, message):
    """Callback when the device receives a message on a subscription."""
    payload = str(message.payload)
    print("*************************************************************************************")
    print(f"Received message '{payload}' on topic '{message.topic}' with Qos {str(message.qos)}")
    print("*************************************************************************************")

def publish(client, mqtt_topic, motion_data, location):
    """Function to publish sensor data to Cloud IoT Core.
    data = [acc_x,acc_y,acc_z,gyro_x,gyro_y,gyro_z]
    """
    payload = {"clientid": platform.uname()[1],
               "motion_data": motion_data,
               "gps": location,
               "timestamp": rfc3339(datetime.datetime.now())
               }
    json_payload = json.dumps(payload)
    print(f"Publishing message: {json_payload}")
    client.publish(mqtt_topic, json_payload, qos=0)
    return


def iot_core_client():
    return get_client(
        project_id,
        cloud_region,
        registry_id,
        device_id,
        private_key_file,
        algorithm,
        ca_certs,
        mqtt_bridge_hostname,
        mqtt_bridge_port
    )
