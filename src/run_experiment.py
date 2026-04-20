#!/usr/bin/python3
"""
One-command reproducible experiment runner (Mininet): MQTT vs CoAP

Examples:
  sudo python3 src/run_experiment.py --protocol mqtt --duration 30 --delay 5ms
  sudo python3 src/run_experiment.py --protocol coap --duration 30 --delay 5ms

Outputs:
results/run_<run_id>/
  meta.json
  logs/
    ...
  mqtt.csv + mqtt.pcap   (if protocol=mqtt)
  coap.csv + coap.pcap   (if protocol=coap)
"""

import argparse
import json
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

from mininet.log import setLogLevel
from topology import build_smart_home_net


def run_cmd(host, cmd, log_file=None, background=True):
    """Run a command inside a Mininet host."""
    if log_file:
        cmd = f"{cmd} > {log_file} 2>&1"
    if background:
        cmd = cmd + " &"
    return host.cmd(cmd)


def pkill(host, pattern):
    host.cmd(f"pkill -f \"{pattern}\" || true")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["mqtt", "coap"], default="mqtt")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--delay", type=str, default="5ms")
    parser.add_argument("--run_id", type=str, default=None)
    parser.add_argument("--results_dir", type=str, default="results")
    parser.add_argument("--mosquitto_conf", type=str, default="configs/mosquitto.conf")
    args = parser.parse_args()

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.results_dir) / f"run_{run_id}"
    logs = outdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    setLogLevel("info")

    # Build + start Mininet topology
    net = build_smart_home_net(delay_sensor=args.delay)
    net.start()

    gateway = net.get("gateway")
    temp1 = net.get("temp1")
    temp2 = net.get("temp2")

    # quick connectivity check
    net.pingAll()

    gateway_ip = gateway.IP()

    # absolute paths for scripts/config
    mosquitto_conf = os.path.abspath(args.mosquitto_conf)
    mqtt_logger_py = os.path.abspath("src/mqtt_logger.py")
    mqtt_sensor_py = os.path.abspath("src/mqtt_sensor.py")
    coap_server_py = os.path.abspath("src/coap_server.py")
    coap_sensor_py = os.path.abspath("src/coap_sensor.py")

    meta = {
        "run_id": run_id,
        "protocol": args.protocol,
        "duration": args.duration,
        "delay": args.delay,
        "hosts": ["gateway", "temp1", "temp2"],
        "gateway_ip": gateway_ip,
        "timestamp": datetime.now().isoformat(),
    }

    if args.protocol == "mqtt":
        csv_path = outdir / "mqtt.csv"
        pcap_path = outdir / "mqtt.pcap"
        port = 1883

        # 1) start broker
        run_cmd(
            gateway,
            f"mosquitto -c {mosquitto_conf}",
            log_file=str(logs / "mosquitto.log"),
            background=True,
        )
        time.sleep(2)

        # 2) start tcpdump
        run_cmd(
            gateway,
            f"tcpdump -i any port {port} -w {pcap_path}",
            log_file=str(logs / "tcpdump_mqtt.log"),
            background=True,
        )
        time.sleep(1)

        # 3) start logger (duration-limited)
        run_cmd(
            gateway,
            f"python3 {mqtt_logger_py} {gateway_ip} {csv_path} --duration {args.duration}",
            log_file=str(logs / "logger_mqtt.log"),
            background=True,
        )
        time.sleep(2)

        # 4) start sensors
        run_cmd(
            temp1,
            f"python3 -u {mqtt_sensor_py} temp1 {gateway_ip}",
            log_file=str(logs / "temp1_mqtt.log"),
            background=True,
        )
        run_cmd(
            temp2,
            f"python3 -u {mqtt_sensor_py} temp2 {gateway_ip}",
            log_file=str(logs / "temp2_mqtt.log"),
            background=True,
        )

    else:  # coap
        csv_path = outdir / "coap.csv"
        pcap_path = outdir / "coap.pcap"
        port = 5683

        # 1) start tcpdump
        run_cmd(
            gateway,
            f"tcpdump -i any udp port {port} -w {pcap_path}",
            log_file=str(logs / "tcpdump_coap.log"),
            background=True,
        )
        time.sleep(1)

        # 2) start coap server on gateway (duration-limited)
        run_cmd(
            gateway,
            f"python3 {coap_server_py} --bind {gateway_ip} --csv {csv_path} --duration {args.duration}",
            log_file=str(logs / "coap_server.log"),
            background=True,
        )
        time.sleep(2)

        # 3) start sensors
        run_cmd(
            temp1,
            f"python3 -u {coap_sensor_py} temp1 {gateway_ip}",
            log_file=str(logs / "temp1_coap.log"),
            background=True,
        )
        run_cmd(
            temp2,
            f"python3 -u {coap_sensor_py} temp2 {gateway_ip}",
            log_file=str(logs / "temp2_coap.log"),
            background=True,
        )

    # Run experiment
    time.sleep(args.duration + 2)

    # Stop processes (protocol-specific)
    if args.protocol == "mqtt":
        pkill(temp1, "mqtt_sensor.py")
        pkill(temp2, "mqtt_sensor.py")
        pkill(gateway, "mqtt_logger.py")
        pkill(gateway, "tcpdump")
        pkill(gateway, "mosquitto")
    else:
        pkill(temp1, "coap_sensor.py")
        pkill(temp2, "coap_sensor.py")
        pkill(gateway, "coap_server.py")
        pkill(gateway, "tcpdump")

    # Save meta
    with open(outdir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Stop Mininet
    net.stop()

    # Fix ownership (so results aren't root-owned)
    user = os.getenv("SUDO_USER")
    if user:
        subprocess.run(["chown", "-R", f"{user}:{user}", str(outdir)], check=False)

    print(f"\nDone. Results written to: {outdir}")
    print(f"- Protocol: {args.protocol}")
    print(f"- CSV:  {csv_path}")
    print(f"- PCAP: {pcap_path}")


if __name__ == "__main__":
    main()