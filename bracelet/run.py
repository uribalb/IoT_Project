import gcp_helpers as gcp
import csv
import math
import datetime
from time import sleep

# ACCELEROMETER AND GYROSCOPE VIRTUAL SENSOR
mpu6050 = {"data": [], "data_length": 0, "index": 0}
STEP_SIZE = 20


def mpu6050_read():
    global mpu6050
    if not mpu6050["data"]:
        with open("data.csv") as csv_file:
            mpu6050["data"] = list(csv.reader(csv_file, delimiter=","))
            mpu6050["data_length"] = len(mpu6050["data"]) - 1
            if mpu6050["data_length"] < 2:
                return [0, 0, 0, 0, 0, 0]
    if mpu6050["index"] < mpu6050["data_length"]:
        mpu6050["index"] += 1
    # Convert values in list to int : [acc_x, acc_y, acc_z, gyro_x, gyro_y,gyro_z]
    return [eval(i) for i in mpu6050["data"][mpu6050["index"]][0:6]]


def gps_read():
    return [14.711521641831823, -17.466275538631095]


def main():
    sub_topic = "events" if gcp.message_type == "event" else "state"
    mqtt_topic = f"/devices/{gcp.device_id}/{sub_topic}"
    jwt_exp_mins = 60
    jwt_iat = datetime.datetime.utcnow()
    print("Initializing connection to Google IoT Core...")
    gcp_iot = gcp.iot_core_client()
    sleep(2)
    trigger1 = False
    trigger2 = False
    # Initialize motion sensor data : [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]
    motion_data = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] for i in range(0, STEP_SIZE)]
    print("Collecting MPU6050 data...")

    while True:
        seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
        # Refresh token after 60 minutes
        if seconds_since_issue > 60 * (jwt_exp_mins - 2):
            print(f"Refreshing token after {seconds_since_issue}s")
            gcp_iot.loop_stop()
            jwt_iat = datetime.datetime.utcnow()
            gcp_iot = gcp.iot_core_client()
        mpu6050_data = mpu6050_read()
        motion_data.pop(0)
        motion_data.append(mpu6050_data)
        g = 9.81
        acc = math.sqrt(math.pow(mpu6050_data[0], 2) + math.pow(mpu6050_data[1], 2) + math.pow(mpu6050_data[2], 2))
        gyro = math.sqrt(math.pow(mpu6050_data[3], 2) + math.pow(mpu6050_data[4], 2) + math.pow(mpu6050_data[5], 2))
        print(f"Acc: {acc}, Gyro: {gyro} ")
        if acc < g and trigger2 is False:
            trigger1 = True
        if trigger1 is True:
            if acc >= 2 * g:
                trigger2 = True
                trigger1 = False
        if trigger2 is True:
            # Send data to cloud
            trigger2 = False
            trigger1 = False
            print(f"*** Suspicious fall event : {mpu6050_data}")
            location = gps_read()
            gcp.publish(gcp_iot, mqtt_topic, motion_data, location)
        sleep(0.5)


if __name__ == "__main__":
    main()
