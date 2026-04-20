#!/usr/bin/python3
"""
CoAP server (gateway) that logs incoming sensor telemetry to CSV.

Sensors POST to:
  coap://10.0.0.1:5683/sensors/<sensor_id>/temperature

Payload expected:
  seq=<int>,temp=<float>,t=<unix_time_float>
"""
import argparse
import asyncio
import csv
import time
from datetime import datetime

import aiocoap.resource as resource
import aiocoap

def parse_kv_payload(payload: str) -> dict:
    out = {}
    for part in payload.split(","):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out

class SensorResource(resource.Resource):
    def __init__(self, csv_writer, start_time):
        super().__init__()
        self.csv_writer = csv_writer
        self.start_time = start_time

    async def render_post(self, request):
        recv_t = time.time()
        elapsed = recv_t - self.start_time
        ts_iso = datetime.fromtimestamp(recv_t).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        path = "/" + "/".join(request.opt.uri_path)  # e.g. /sensors/temp1/temperature
        parts = list(request.opt.uri_path)
        sensor_id = parts[1] if len(parts) > 1 else "unknown"
        metric_type = parts[2] if len(parts) > 2 else "unknown"

        payload = request.payload.decode(errors="replace")
        kv = parse_kv_payload(payload)

        sensor_id = kv.get("sid", "unknown")
        metric_type = kv.get("metric", "unknown")
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
            "coap",
            sensor_id,
            metric_type,
            value,
            seq,
            client_send,
            latency_ms,
            "",
            "",
            path,
            "2.04 Changed",
        ])

        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"OK")

async def main_async(bind_ip, csv_path, duration):
    start_time = time.time()

    csv_file = open(csv_path, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow([
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

    root = resource.Site()
    # attach resource at /sensors/...
    sensors = resource.Site()
    root.add_resource(["sensors"], sensors)

    # wildcard-like behavior: add a handler at /sensors and parse uri_path inside
    # simplest: register a single resource at /sensors and accept any deeper uri_path
    # aiocoap doesn't do true wildcards; we register exact depth paths dynamically is complex,
    # so we register a resource at /sensors and also common sensor paths used in our runner:
    handler = SensorResource(writer, start_time)
    for sid in ["temp1", "temp2"]:
        sensors.add_resource([sid, "temperature"], handler)

    context = await aiocoap.Context.create_server_context(root, bind=(bind_ip, 5683))
    try:
        await asyncio.sleep(duration)
    finally:
        csv_file.flush()
        csv_file.close()
        await context.shutdown()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="10.0.0.1")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--duration", type=int, default=30)
    args = parser.parse_args()

    asyncio.run(main_async(args.bind, args.csv, args.duration))

if __name__ == "__main__":
    main()