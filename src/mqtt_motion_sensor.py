#!/usr/bin/python3
"""MQTT Motion Sensor - Event-driven"""
import paho.mqtt.client as mqtt
import time
import random
import sys

def main():
    sensor_id = sys.argv[1] if len(sys.argv) > 1 else "motion1"
    broker_ip = sys.argv[2] if len(sys.argv) > 2 else "10.0.0.1"
    
    client = mqtt.Client(client_id=sensor_id)
    
    print(f"[{sensor_id}] Connecting to broker at {broker_ip}...")
    client.connect(broker_ip, 1883, 60)
    
    print(f"[{sensor_id}] Motion detector active - monitoring area...")
    
    try:
        event_count = 0
        while True:
            time.sleep(random.uniform(5, 15))
            
            if random.random() < 0.3:
                event_count += 1
                timestamp = time.strftime("%H:%M:%S")
                topic = f"sensors/{sensor_id}/motion"
                payload = f"MOTION_DETECTED,{timestamp},event_{event_count}"
                client.publish(topic, payload)
                print(f"[{sensor_id}] ⚠️  Event #{event_count}: Motion detected at {timestamp}")
            
    except KeyboardInterrupt:
        print(f"\n[{sensor_id}] Shutting down - Total events: {event_count}")
        client.disconnect()

if __name__ == '__main__':
    main()
