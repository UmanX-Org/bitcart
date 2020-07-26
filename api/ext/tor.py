import ipaddress
import os
from collections import namedtuple  # TODO: dataclasses

from .. import settings

HiddenService = namedtuple(
    "HiddenService", ["name", "directory", "hostname", "port_definition"]
)
PortDefinition = namedtuple("PortDefinition", ["virtual_port", "ip", "port"])


def is_onion(host):
    return host.lower().endswith(".onion")


def parse_hidden_service(line):
    if not line.startswith("HiddenServiceDir "):
        return
    parts = line.split()
    if len(parts) != 2:
        return
    return parts[1].strip()


def parse_hidden_service_port(line):
    if not line.startswith("HiddenServicePort "):
        return
    parts = line.split()
    if len(parts) != 3:
        return
    try:
        virtual_port = int(parts[1].strip())
        address_port = parts[2].strip().split(":")
        if len(address_port) != 2:
            return
        port = int(address_port[1])
        ip_address = ipaddress.ip_address(address_port[0].strip())
        return PortDefinition(virtual_port, ip_address, port)
    except ValueError:
        return  # all parsing exceptions are ValueError


def get_hostname(service_dir):
    path = os.path.join(service_dir, "hostname")
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            return f"http://{f.readline().strip()}"
    except OSError:
        return


def get_service_name(service_dir):
    return os.path.basename(service_dir).replace("-", " ")


def parse_torrc(torrc):
    if not torrc or not os.path.exists(torrc):
        return []
    try:
        with open(torrc) as f:
            lines = f.readlines()
    except OSError:
        return []
    services = []
    for line in lines:
        line = line.strip()
        hidden_service = parse_hidden_service(line)
        hidden_service_port = parse_hidden_service_port(line)
        if hidden_service:
            hidden_service = HiddenService(
                get_service_name(hidden_service),
                hidden_service,
                get_hostname(hidden_service),
                None,
            )
            services.append(hidden_service)
        elif hidden_service_port and services:
            services[-1] = services[-1]._replace(port_definition=hidden_service_port)
    return services


services = parse_torrc(settings.TORRC_FILE)
services_dict = {service.name: service._asdict() for service in services}
anonymous_services_dict = {
    service.name: {"name": service.name, "hostname": service.hostname}
    for service in services
}
onion_host = services_dict.get("BitcartCC-Merchants-API", "")
if onion_host:
    onion_host = onion_host["hostname"]
