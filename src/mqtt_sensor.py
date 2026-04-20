#!/usr/bin/python3
"""MQTT Temperature Sensor Simulator (with seq + client timestamp payload)"""
import paho.mqtt.client as mqtt
import time
import random
import sys

def main():
    sensor_id = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    broker_ip = sys.argv[2] if len(sys.argv) > 2 else "10.0.0.1"

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client._client_id = sensor_id.encode("utf-8")

    print(f"[{sensor_id}] Connecting to {broker_ip}:1883...", flush=True)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            client.connect(broker_ip, 1883, 60)
            print(f"[{sensor_id}] ✓ Connected!", flush=True)
            break
        except Exception:
            if attempt < max_retries - 1:
                print(f"[{sensor_id}] Retry in 2s...", flush=True)
                time.sleep(2)
            else:
                print(f"[{sensor_id}] Failed to connect. Exiting.", flush=True)
                return

    seq = 0
    try:
        while True:
            seq += 1
            temp = round(random.uniform(18.0, 26.0), 2)
            client_send_t = time.time()

            topic = f"sensors/{sensor_id}/temperature"
            payload = f"sid={sensor_id},metric=temperature,seq={seq},temp={temp},t={client_send_t:.6f}"

            client.publish(topic, payload)
            print(f"[{sensor_id}] seq={seq} temp={temp} t={client_send_t:.6f}", flush=True)
            time.sleep(3)
    except KeyboardInterrupt:
        print(f"\n[{sensor_id}] Stopped.", flush=True)
        client.disconnect()

if __name__ == "__main__":
    main()