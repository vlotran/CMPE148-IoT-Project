#!/usr/bin/python3
"""
Centralized MQTT Data Logger (unified CSV schema + duration auto-stop)

Subscribes to sensors/# and expects payload:
  seq=<int>,temp=<float>,t=<unix_time_float>
"""
import paho.mqtt.client as mqtt
import time
import csv
import argparse
import signal
from datetime import datetime

def parse_kv_payload(payload: str) -> dict:
    out = {}
    for part in payload.split(","):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out

class MQTTLogger:
    def __init__(self, broker_ip, output_file="mqtt.csv"):
        self.broker_ip = broker_ip
        self.output_file = output_file
        self.message_count = 0
        self.start_time = time.time()
        self.stopped = False

        self.csv_file = open(output_file, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)

        # Unified schema (same columns for MQTT and CoAP)
        self.csv_writer.writerow([
            "timestamp_iso",
            "unix_time",
            "elapsed_s",
            "protocol",
            "sensor_id",
            "metric_type",
            "value",
            "seq",
            "client_send_unix_time",
            "latency_ms",
            "mqtt_topic",
            "mqtt_qos",
            "coap_path",
            "coap_code",
        ])

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"[MQTT-Logger] Connected to broker at {self.broker_ip}")
        client.subscribe("sensors/#")
        print("[MQTT-Logger] Subscribed to sensors/#")
        print(f"[MQTT-Logger] Logging to: {self.output_file}")
        print("=" * 60)

    def on_message(self, client, userdata, msg):
        if self.stopped:
            return

        recv_t = time.time()
        elapsed = recv_t - self.start_time
        ts_iso = datetime.fromtimestamp(recv_t).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        topic = msg.topic
        qos = msg.qos
        payload = msg.payload.decode(errors="replace")

        parts = topic.split("/")
        sensor_id = parts[1] if len(parts) > 1 else "unknown"
        metric_type = parts[2] if len(parts) > 2 else "unknown"

        kv = parse_kv_payload(payload)
        sensor_id = kv.get("sid", sensor_id)
        metric_type = kv.get("metric", metric_type)
        seq = kv.get("seq", "")
        value = kv.get("temp", kv.get("value", ""))
        client_send = kv.get("t", "")

        latency_ms = ""
        try:
            if client_send != "":
                latency_ms = (recv_t - float(client_send)) * 1000.0
                latency_ms = f"{latency_ms:.3f}"
        except Exception:
            latency_ms = ""

        self.csv_writer.writerow([
            ts_iso,
            f"{recv_t:.6f}",
            f"{elapsed:.3f}",
            "mqtt",
            sensor_id,
            metric_type,
            value,
            seq,
            client_send,
            latency_ms,
            topic,
            qos,
            "",
            "",
        ])

        self.message_count += 1
        if self.message_count % 10 == 0:
            self.csv_file.flush()

    def run(self, duration=None):
        def _alarm_handler(signum, frame):
            self.stop()
            raise SystemExit(0)

        try:
            self.client.connect(self.broker_ip, 1883, 60)
            if duration is not None:
                signal.signal(signal.SIGALRM, _alarm_handler)
                signal.alarm(int(duration))
            self.client.loop_forever()
        except (KeyboardInterrupt, SystemExit):
            self.stop()
        except Exception as e:
            print(f"[MQTT-Logger] Error: {e}")
            self.stop()

    def stop(self):
        if self.stopped:
            return
        self.stopped = True
        try:
            self.csv_file.flush()
            self.csv_file.close()
        except Exception:
            pass
        try:
            self.client.disconnect()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("broker_ip")
    parser.add_argument("output_file")
    parser.add_argument("--duration", type=int, default=None)
    args = parser.parse_args()

    MQTTLogger(args.broker_ip, args.output_file).run(duration=args.duration)

if __name__ == "__main__":
    main()