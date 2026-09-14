"""Regression tests for the coordinator callback without a running HA instance.

Run with: python -m unittest discover -s tests -v
The integration's pysma-plus dependency must be installed.
"""

import ast
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pysmaplus as pysma

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/pysmaplus/__init__.py"


class UpdateFailed(Exception):
    """Stand-in for HA's coordinator exception in this isolated callback test."""


def load_update_callback(device):
    """Load the actual nested callback while replacing only its HA context."""
    tree = ast.parse(SOURCE.read_text())
    setup = next(
        node
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry"
    )
    callback = next(
        node
        for node in setup.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_update_data"
    )
    namespace = {
        "pysma": pysma,
        "sma": device,
        "sensor_def": [],
        "entry": SimpleNamespace(
            data={"host": "test-inverter", "access": "ennexos", "device": "IGULD:SELF"}
        ),
        "CONF_HOST": "host",
        "CONF_ACCESS": "access",
        "CONF_DEVICE": "device",
        "_LOGGER": logging.getLogger("test.pysmaplus.coordinator"),
        "UpdateFailed": UpdateFailed,
    }
    exec(
        compile(ast.Module(body=[callback], type_ignores=[]), str(SOURCE), "exec"),
        namespace,
    )
    return namespace["async_update_data"]


class AuthenticationFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_authentication_failure_is_an_update_failure(self):
        error = pysma.exceptions.SmaAuthenticationException("HTTP 401 after retry")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await load_update_callback(device)()
        self.assertIs(caught.exception.__cause__, error)
        device.read.assert_awaited_once()

    async def test_connection_failure_remains_an_update_failure(self):
        error = pysma.exceptions.SmaConnectionException("Disconnected")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await load_update_callback(device)()
        self.assertIs(caught.exception.__cause__, error)

    async def test_successful_read_remains_successful(self):
        device = SimpleNamespace(read=AsyncMock(return_value=True))
        with self.assertNoLogs("test.pysmaplus.coordinator", level="WARNING"):
            self.assertIsNone(await load_update_callback(device)())
        device.read.assert_awaited_once_with([], "IGULD:SELF")


if __name__ == "__main__":
    unittest.main()
