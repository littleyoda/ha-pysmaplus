"""Regression tests for entry-setup failures that must be retried by Home Assistant.

Run with: python -m unittest discover -s tests -v
The integration's pysma-plus dependency must be installed.

A SpeedwireEM entry (Energy Meter / Sunny Home Manager 2) whose first multicast
datagram does not arrive in time - typically right after a host reboot, before
the network or the IGMP join is ready - raises SmaMulticastReceiveException from
SMAspeedwireEM.new_session(). Setup has to turn that into ConfigEntryNotReady so
Home Assistant retries the entry instead of leaving it in setup_error forever.

The SpeedwireEM tests drive the real getPysmaInstance / async_setup_entry code
against the real SMAspeedwireEM device over real UDP sockets. Only the socket
factory is redirected to an ephemeral loopback port, so the tests neither need
port 9522 nor pick up a live energy meter's multicast on the test machine.
"""

import ast
import asyncio
import base64
import contextlib
import json
import logging
import socket
import struct
import time
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pysmaplus as pysma
from pysmaplus.device_em import SMAspeedwireEM

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/pysmaplus/__init__.py"
# Sample SHM2 telegram from the pysma-plus test suite (tests/testdata/SunnyHomeManager2.json).
SHM2_PACKET = base64.b64decode(
    json.loads((Path(__file__).parent / "testdata/SunnyHomeManager2.json").read_text())[
        "packet"
    ]
)


class ConfigEntryNotReady(Exception):
    """Stand-in for HA's ConfigEntryNotReady in these isolated setup tests."""


class ReachedCoordinator(Exception):
    """Raised once setup has got past the guarded device-initialisation block."""


def load_setup_functions():
    """Load the real getPysmaInstance and async_setup_entry with isolated HA context."""
    tree = ast.parse(SOURCE.read_text())
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name in ("getPysmaInstance", "async_setup_entry")
    ]

    def coordinator(*args, **kwargs):
        raise ReachedCoordinator

    namespace = {
        "HomeAssistant": object,
        "ConfigEntry": object,
        "Device": object,
        "Any": object,
        "TYPE_CHECKING": False,
        "pysma": pysma,
        "network": SimpleNamespace(
            async_get_adapters=AsyncMock(
                return_value=[
                    {"name": "lo", "enabled": True, "ipv4": [{"address": "127.0.0.1"}]}
                ]
            )
        ),
        "async_get_clientsession": Mock(),
        "_LOGGER": logging.getLogger("test.pysmaplus.setup"),
        "ConfigEntryNotReady": ConfigEntryNotReady,
        "DeviceInfo": dict,
        "DataUpdateCoordinator": coordinator,
        "timedelta": timedelta,
        "DOMAIN": "pysmaplus",
        "CONF_ACCESS": "access",
        "CONF_DEVICE": "device",
        "CONF_GROUP": "group",
        "CONF_HOST": "host",
        "CONF_PASSWORD": "password",
        "CONF_RETRIES": "retries",
        "CONF_SCAN_INTERVAL": "scan_interval",
        "CONF_SSL": "ssl",
        "CONF_VERIFY_SSL": "verify_ssl",
    }
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"),
        namespace,
    )
    return namespace["async_setup_entry"]


def speedwireem_entry(device_id="0"):
    return SimpleNamespace(
        unique_id="em-test",
        entry_id="test-entry",
        options={},
        data={
            "access": "speedwireem",
            "host": "",
            "password": "",
            "ssl": False,
            "verify_ssl": False,
            "group": "user",
            "device": device_id,
            "scan_interval": 5,
        },
    )


class LoopbackSocket:
    """Replaces SMAspeedwireEM._getDiscoverySocket with an ephemeral loopback socket."""

    def __init__(self):
        self.port = None

    def __call__(self, device):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        sock.setblocking(False)
        self.port = sock.getsockname()[1]
        device._sock = sock
        return sock


async def send_shm2_packets(loopback):
    """Send the sample SHM2 telegram to the loopback socket, like a live meter would.

    Each telegram gets a fresh timestamp (bytes 24-28), as SMAspeedwireEM drops
    repeated telegrams with the same sender and timestamp.
    """
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
            if loopback.port is not None:
                packet = bytearray(SHM2_PACKET)
                packet[24:28] = struct.pack(">I", int(time.time() * 1000) & 0xFFFFFFFF)
                sender.sendto(packet, ("127.0.0.1", loopback.port))
            await asyncio.sleep(0.2)
    finally:
        sender.close()


class SpeedwireEMSetupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.loopback = LoopbackSocket()
        patcher = patch.object(
            SMAspeedwireEM, "_getDiscoverySocket", autospec=True, side_effect=self.loopback
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.devices = []
        get_device = pysma.getDevice

        def tracking_get_device(*args, **kwargs):
            device = get_device(*args, **kwargs)
            self.devices.append(device)
            return device

        patcher = patch.object(pysma, "getDevice", side_effect=tracking_get_device)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        for device in self.devices:
            await device.close_session()

    async def test_no_multicast_packet_is_not_ready(self):
        setup = load_setup_functions()
        with self.assertRaises(ConfigEntryNotReady) as caught:
            await setup(object(), speedwireem_entry())
        self.assertIsInstance(
            caught.exception.__cause__, pysma.exceptions.SmaMulticastReceiveException
        )
        self.assertIsInstance(caught.exception.__cause__.__cause__, TimeoutError)

    async def test_received_packets_complete_device_initialisation(self):
        serial = SMAspeedwireEM().datagram_received(SHM2_PACKET, ("127.0.0.1", 9522))[
            "serial"
        ]
        setup = load_setup_functions()
        sender = asyncio.create_task(send_shm2_packets(self.loopback))
        try:
            with self.assertRaises(ReachedCoordinator):
                await setup(object(), speedwireem_entry(str(serial)))
        finally:
            sender.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sender


if __name__ == "__main__":
    unittest.main()
