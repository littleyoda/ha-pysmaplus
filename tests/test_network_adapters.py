"""Regression tests for SpeedwireEM network adapter selection.

Run with: python -m unittest discover -s tests -v
"""

import ast
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/pysmaplus/__init__.py"


def load_get_pysma_instance(device, adapters):
    """Load the real getPysmaInstance function with isolated dependencies."""
    tree = ast.parse(SOURCE.read_text())

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name in ("async_setup", "getPysmaInstance")
    ]

    fake_pysma = SimpleNamespace(
        getDevice=Mock(return_value=device),
    )

    fake_network = SimpleNamespace(
        async_get_adapters=AsyncMock(return_value=adapters),
    )

    namespace = {
        "HomeAssistant": object,
        "ConfigType": dict,
        "Device": object,
        "Any": object,
        "pysma": fake_pysma,
        "network": fake_network,
        "async_get_clientsession": Mock(),
        "_LOGGER": logging.getLogger("test.pysmaplus.network"),
        "CONF_ACCESS": "access",
        "CONF_ENERGY_METER_BIND_TO_ALL_INTERFACES": "energy_meter_bind_to_all_interfaces",
        "DOMAIN": "pysmaplus",
        "CONF_HOST": "host",
        "CONF_PASSWORD": "password",
        "CONF_SSL": "ssl",
        "CONF_VERIFY_SSL": "verify_ssl",
        "CONF_GROUP": "group",
        "CONF_RETRIES": "retries",
    }

    exec(
        compile(
            ast.Module(body=functions, type_ignores=[]),
            str(SOURCE),
            "exec",
        ),
        namespace,
    )

    return namespace["getPysmaInstance"], namespace["async_setup"], fake_network


class NetworkAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_speedwireem_uses_only_enabled_network_adapters(self):
        device = SimpleNamespace(
            set_options=Mock(),
            new_session=AsyncMock(),
        )

        adapters = [
            {
                "name": "eno1",
                "enabled": True,
                "ipv4": [{"address": "192.168.2.10"}],
            },
            {
                "name": "br-test",
                "enabled": False,
                "ipv4": [{"address": "192.168.48.1"}],
            },
        ]

        get_pysma_instance, _, fake_network = load_get_pysma_instance(device, adapters)

        data = {
            "access": "speedwireem",
            "host": "",
            "password": "",
            "ssl": False,
            "verify_ssl": False,
            "group": "user",
        }

        result = await get_pysma_instance(SimpleNamespace(data={}), data)

        self.assertIs(result, device)
        fake_network.async_get_adapters.assert_awaited_once()
        device.set_options.assert_called_once_with({"bindingaddr": "192.168.2.10"})
        device.new_session.assert_awaited_once()

    async def test_yaml_override_controls_binding_for_energy_meters(self):
        for config, bind_to_all in (
            ({}, False),
            ({"pysmaplus": None}, False),
            ({"pysmaplus": {}}, False),
            ({"pysmaplus": {"energy_meter_bind_to_all_interfaces": False}}, False),
            ({"pysmaplus": {"energy_meter_bind_to_all_interfaces": True}}, True),
        ):
            for access in ("speedwireem", "speedwire"):
                with self.subTest(config=config, access=access):
                    device = SimpleNamespace(set_options=Mock(), new_session=AsyncMock())
                    adapters = [{"enabled": True, "ipv4": [{"address": "192.168.2.10"}]}]
                    get_instance, setup, network = load_get_pysma_instance(device, adapters)
                    existing_entry = {"pysma": object()}
                    hass = SimpleNamespace(data={"pysmaplus": {"existing": existing_entry}})

                    self.assertTrue(await setup(hass, config))
                    self.assertIs(hass.data["pysmaplus"]["existing"], existing_entry)
                    result = await get_instance(hass, {
                        "access": access,
                        "host": "",
                        "password": "",
                        "ssl": False,
                        "verify_ssl": False,
                        "group": "user",
                    })

                    self.assertIs(result, device)
                    if bind_to_all:
                        network.async_get_adapters.assert_not_awaited()
                        device.set_options.assert_not_called()
                    else:
                        network.async_get_adapters.assert_awaited_once_with(hass)
                        device.set_options.assert_called_once_with({"bindingaddr": "192.168.2.10"})
                    device.new_session.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
