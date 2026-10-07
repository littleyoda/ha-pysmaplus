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

    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "getPysmaInstance"
    )

    fake_pysma = SimpleNamespace(
        getDevice=Mock(return_value=device),
    )

    fake_network = SimpleNamespace(
        async_get_adapters=AsyncMock(return_value=adapters),
    )

    namespace = {
        "HomeAssistant": object,
        "Device": object,
        "Any": object,
        "pysma": fake_pysma,
        "network": fake_network,
        "async_get_clientsession": Mock(),
        "_LOGGER": logging.getLogger("test.pysmaplus.network"),
        "CONF_ACCESS": "access",
        "CONF_HOST": "host",
        "CONF_PASSWORD": "password",
        "CONF_SSL": "ssl",
        "CONF_VERIFY_SSL": "verify_ssl",
        "CONF_GROUP": "group",
        "CONF_RETRIES": "retries",
    }

    exec(
        compile(
            ast.Module(body=[function], type_ignores=[]),
            str(SOURCE),
            "exec",
        ),
        namespace,
    )

    return namespace["getPysmaInstance"], fake_pysma, fake_network


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

        result = await get_pysma_instance(object(), data)

        self.assertIs(result, device)
        fake_network.async_get_adapters.assert_awaited_once()
        device.set_options.assert_called_once_with({"bindingaddr": "192.168.2.10"})
        device.new_session.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
