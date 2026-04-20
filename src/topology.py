#!/usr/bin/python3
from mininet.net import Mininet
from mininet.link import TCLink

def build_smart_home_net(
    delay_sensor="5ms",
    bw_sensor=10,
    bw_gateway=100,
):
    """
    Star topology (simplified MVP):
      gateway + temp1 + temp2 connected to switch s1.

    Returns:
      net (Mininet)
    """
    net = Mininet(link=TCLink, autoSetMacs=True)

    # standalone learning switch (no controller needed)
    s1 = net.addSwitch("s1", failMode="standalone")

    gateway = net.addHost("gateway", ip="10.0.0.1/24")
    temp1   = net.addHost("temp1",   ip="10.0.0.11/24")
    temp2   = net.addHost("temp2",   ip="10.0.0.12/24")

    # links
    net.addLink(gateway, s1, bw=bw_gateway)
    net.addLink(temp1, s1, bw=bw_sensor, delay=delay_sensor)
    net.addLink(temp2, s1, bw=bw_sensor, delay=delay_sensor)

    return net