#!/usr/bin/python3
"""CoAP Temperature Sensor Simulator (seq + client timestamp payload)"""
import asyncio
import argparse
import random
import time
import aiocoap

async def run(sensor_id, gateway_ip):
    protocol = await aiocoap.Context.create_client_context()
    seq = 0
    try:
        while True:
            seq += 1
            temp = round(random.uniform(18.0, 26.0), 2)
            client_send_t = time.time()
            payload = f"sid={sensor_id},metric=temperature,seq={seq},temp={temp},t={client_send_t:.6f}".encode()

            # IMPORTANT: send uri_path explicitly
            req = aiocoap.Message(
                code=aiocoap.POST,
                uri=f"coap://{gateway_ip}:5683",
                uri_path=("sensors", sensor_id, "temperature"),
                payload=payload,
            )

            try:
                await protocol.request(req).response
            except Exception:
                pass

            await asyncio.sleep(3)
    finally:
        await protocol.shutdown()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sensor_id")
    parser.add_argument("gateway_ip")
    args = parser.parse_args()
    asyncio.run(run(args.sensor_id, args.gateway_ip))

if __name__ == "__main__":
    main()