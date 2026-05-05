#!/usr/bin/python3
from mininet.net import Mininet
from mininet.link import TCLink

def build_smart_home_net(
    num_sensors=2,
    delay_sensor="5ms",
    bw_sensor=10,
    bw_gateway=100,
  ):
    """
    Star topology (simplified MVP):
      gateway + temp[i] connected to switch s1.

    Returns:
      net (Mininet)
    """
    net = Mininet(link=TCLink, autoSetMacs=True)

    # standalone learning switch (no controller needed)
    s1 = net.addSwitch("s1", failMode="standalone")

    gateway = net.addHost("gateway", ip="10.0.0.1/24")
    net.addLink(gateway, s1, bw=bw_gateway)

    for i in range(1, num_sensors + 1):
        sensor = net.addHost(f"temp{i}", ip=f"10.0.0.{10+i}/24")
        net.addLink(sensor, s1, bw=bw_sensor, delay=delay_sensor)

    return net