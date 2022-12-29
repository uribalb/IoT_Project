import base64
import functions_framework
import json
from google.cloud import bigquery
from google.cloud import iot_v1
from google.cloud import aiplatform


# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def handle_motion_data(cloud_event):
   # Parameters - Cloud IoT Core
   project_id = cloud_event.data["message"]["attributes"]["projectId"]
   cloud_region = cloud_event.data["message"]["attributes"]["deviceRegistryLocation"]
   registry_id = cloud_event.data["message"]["attributes"]["deviceRegistryId"]
   device_id = cloud_event.data["message"]["attributes"]["deviceId"]

   # Parameter
   bq_dataset = "dataset_iot_sadio"  # change prenom suffix by your name
   bq_table = "bracelet"
   vertex_ai_endpoint = "527646834076680192"

   # Pub/Sub data
   data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
   data_dict = json.loads(data)
   
   # Insert in BigQuery
   bq_client = bigquery.Client()
   table_id = bigquery.Table.from_string(f"{project_id}.{bq_dataset}.{bq_table}")
   rows_to_insert = []
   for motion in data_dict["motion_data"]:
      rows_to_insert.append({
         "acc_x": motion[0],
         "acc_y": motion[1],
         "acc_z": motion[2],
         "gyro_x": motion[3],
         "gyro_y": motion[4],
         "gyro_z": motion[5],
         "latitude": data_dict["gps"][0],
         "longitude": data_dict["gps"][1],
         "device_id": device_id,
         "timestamp": data_dict["timestamp"]
      })
   errors = bq_client.insert_rows_json(table_id, rows_to_insert)
   if errors:
      print(f"Encountered errors while inserting rows: {errors}")

   # Predict with Vertex AI
   aiplatform.init(project=project_id, location=cloud_region)
   endpoint = aiplatform.Endpoint(vertex_ai_endpoint)

   prediction = endpoint.predict(instances=data_dict["motion_data"])
   max_prediction = max(prediction[0][0])
   class_index = prediction[0][0].index(max_prediction)

   class_names = { 0:'STD', 1:'WAL', 2:'JOG' , 3:'JUM', 4:'FALL', 5:'LYI', 6:'RA'}
   motion_type = class_names[class_index]
   print(motion_type)

   if motion_type == "FALL":
      print("Sending command to device")
      iot_client = iot_v1.DeviceManagerClient()
      device_path = iot_client.device_path(project_id, cloud_region, registry_id, device_id)
      data = motion_type.encode("utf-8")
      iot_client.send_command_to_device(request={"name": device_path, "binary_data": data})



