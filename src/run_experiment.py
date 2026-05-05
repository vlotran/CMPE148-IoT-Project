#!/usr/bin/python3

"""
One-command reproducible experiment runner using Mininet.

This script runs an MQTT or CoAP smart-home experiment inside a Mininet
network. It starts the required gateway services, launches sensor clients,
captures traffic using tcpdump, stores experiment metadata, and saves results
to a run-specific output directory.
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
    """
    Run a shell command inside a Mininet host.

    Parameters:
        host: Mininet host object where the command will run.
        cmd: Command string to execute.
        log_file: Optional file path where stdout/stderr should be redirected.
        background: If True, run the command in the background.
    """

    # Redirect both standard output and standard error to a log file if provided.
    if log_file:
        cmd = f"{cmd} > {log_file} 2>&1"

    # Append '&' so long-running services continue in the background.
    if background:
        cmd = cmd + " &"

    return host.cmd(cmd)


def pkill(host, pattern):
    """
    Kill processes running inside a Mininet host that match a given pattern.

    The command is allowed to fail silently if no matching process exists.
    """

    host.cmd(f"pkill -f \"{pattern}\" || true")

def count_csv_rows(csv_path):
    """
    Count data rows in a CSV file, excluding the header row.
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        return 0

    with open(csv_path, "r") as f:
        return max(sum(1 for _ in f) - 1, 0)


def main():
    """
    Parse command-line arguments, build the Mininet topology, run the selected
    protocol experiment, collect logs/pcaps/CSVs, and clean up resources.
    """

    # -----------------------------
    # Command-line argument parsing
    # -----------------------------
    parser = argparse.ArgumentParser()

    parser.add_argument("--protocol", choices=["mqtt", "coap"], default="mqtt")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--delay", type=str, default="5ms")
    parser.add_argument("--run_id", type=str, default=None)
    parser.add_argument("--results_dir", type=str, default="results")
    parser.add_argument("--mosquitto_conf", type=str, default="configs/mosquitto.conf")
    parser.add_argument("--sensors", type=int, default=2)
    parser.add_argument("--bw_sensor", type=float, default=10)
    parser.add_argument("--bw_gateway", type=float, default=100)

    args = parser.parse_args()

    # Create a unique run ID if the user did not provide one.
    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create output directories for this experiment run.
    outdir = Path(args.results_dir) / f"run_{run_id}"
    logs = outdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    # Enable Mininet informational logging.
    setLogLevel("info")

    # Initialize variables so they are available in the cleanup block.
    net = None
    gateway = None
    sensors = []
    csv_path = None
    pcap_path = None

    try:
        # -----------------------------
        # Build and start Mininet network
        # -----------------------------
        net = build_smart_home_net(
            num_sensors=args.sensors,
            delay_sensor=args.delay,
            bw_sensor=args.bw_sensor,
            bw_gateway=args.bw_gateway,
        )
        net.start()

        # Get references to the gateway and sensor hosts.
        gateway = net.get("gateway")
        sensors = [net.get(f"temp{i}") for i in range(1, args.sensors + 1)]

        # Verify basic network connectivity.
        net.pingAll()

        # Get the gateway IP address, used by sensors and logging services.
        gateway_ip = gateway.IP()

        # Resolve script/config paths to absolute paths.
        mosquitto_conf = os.path.abspath(args.mosquitto_conf)
        mqtt_logger_py = os.path.abspath("src/mqtt_logger.py")
        mqtt_sensor_py = os.path.abspath("src/mqtt_sensor.py")
        coap_server_py = os.path.abspath("src/coap_server.py")
        coap_sensor_py = os.path.abspath("src/coap_sensor.py")

        # Store metadata describing the experiment configuration.
        meta = {
            "run_id": run_id,
            "protocol": args.protocol,
            "duration": args.duration,
            "delay": args.delay,
            "num_sensors": args.sensors,
            "bw_sensor": args.bw_sensor,
            "bw_gateway": args.bw_gateway,
            "hosts": ["gateway"] + [f"temp{i}" for i in range(1, args.sensors + 1)],
            "gateway_ip": gateway_ip,
            "timestamp": datetime.now().isoformat(),
        }

        # -----------------------------
        # MQTT experiment setup
        # -----------------------------
        if args.protocol == "mqtt":
            csv_path = outdir / "mqtt.csv"
            pcap_path = outdir / "mqtt.pcap"
            port = 1883

            # Start Mosquitto MQTT broker on the gateway.
            run_cmd(
                gateway,
                f"mosquitto -c {mosquitto_conf}",
                log_file=str(logs / "mosquitto.log"),
                background=True,
            )
            time.sleep(2)

            # Start packet capture for MQTT traffic.
            run_cmd(
                gateway,
                f"tcpdump -i any port {port} -w {pcap_path}",
                log_file=str(logs / "tcpdump_mqtt.log"),
                background=True,
            )
            time.sleep(1)

            # Start MQTT logger to subscribe to sensor data and write CSV output.
            run_cmd(
                gateway,
                f"python3 {mqtt_logger_py} {gateway_ip} {csv_path} --duration {args.duration}",
                log_file=str(logs / "logger_mqtt.log"),
                background=True,
            )
            time.sleep(2)

            # Start one MQTT sensor process per sensor host.
            for i, sensor in enumerate(sensors, start=1):
                sid = f"temp{i}"
                run_cmd(
                    sensor,
                    f"python3 -u {mqtt_sensor_py} {sid} {gateway_ip}",
                    log_file=str(logs / f"{sid}_mqtt.log"),
                    background=True,
                )

        # -----------------------------
        # CoAP experiment setup
        # -----------------------------
        else:
            csv_path = outdir / "coap.csv"
            pcap_path = outdir / "coap.pcap"
            port = 5683

            # Start packet capture for CoAP UDP traffic.
            run_cmd(
                gateway,
                f"tcpdump -i any udp port {port} -w {pcap_path}",
                log_file=str(logs / "tcpdump_coap.log"),
                background=True,
            )
            time.sleep(1)

            # Start CoAP server on the gateway and write received data to CSV.
            run_cmd(
                gateway,
                f"python3 {coap_server_py} --bind {gateway_ip} --csv {csv_path} --duration {args.duration} --sensors {args.sensors}",
                log_file=str(logs / "coap_server.log"),
                background=True,
            )
            time.sleep(2)

            # Start one CoAP sensor process per sensor host.
            for i, sensor in enumerate(sensors, start=1):
                sid = f"temp{i}"
                run_cmd(
                    sensor,
                    f"python3 -u {coap_sensor_py} {sid} {gateway_ip}",
                    log_file=str(logs / f"{sid}_coap.log"),
                    background=True,
                )

        # Allow the experiment to run for the requested duration.
        # The extra 2 seconds helps ensure late packets/logs are captured.
        time.sleep(args.duration + 2)

        expected_min_rows = args.sensors

        rows = count_csv_rows(csv_path)

        if rows < expected_min_rows:
           raise RuntimeError(
           f"{args.protocol.upper()} produced too few CSV rows: {rows}.\n"
           f"Expected at least {expected_min_rows} rows for {args.sensors} sensors.\n"
           f"CSV file: {csv_path}\n"
           f"Check logs in: {logs}"
        )

        # Save experiment metadata after the run completes.
        with open(outdir / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        # Print a short summary for the user.
        print(f"\nDone. Results written to: {outdir}")
        print(f"- Protocol: {args.protocol}")
        print(f"- CSV:  {csv_path}")
        print(f"- PCAP: {pcap_path}")

    except KeyboardInterrupt:
        # Allow graceful exit if the user stops the experiment manually.
        print("\nInterrupted by user.")

    finally:
        # -----------------------------
        # Cleanup processes
        # -----------------------------
        if gateway is not None:
            if args.protocol == "mqtt":
                # Stop MQTT sensor clients, logger, tcpdump, and broker.
                for sensor in sensors:
                    pkill(sensor, "mqtt_sensor.py")

                pkill(gateway, "mqtt_logger.py")
                pkill(gateway, "tcpdump")
                pkill(gateway, "mosquitto")

            else:
                # Stop CoAP sensor clients, server, and tcpdump.
                for sensor in sensors:
                    pkill(sensor, "coap_sensor.py")

                pkill(gateway, "coap_server.py")
                pkill(gateway, "tcpdump")

        # Stop the Mininet network if it was started.
        if net is not None:
            net.stop()

        # If the script was run with sudo, return ownership of result files
        # to the original user so they can edit/delete them without sudo.
        user = os.getenv("SUDO_USER")
        if user:
            subprocess.run(["chown", "-R", f"{user}:{user}", str(outdir)], check=False)


if __name__ == "__main__":
    main()