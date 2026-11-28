"""Regression tests for the coordinator callback without a running HA instance.

Run with: python -m unittest discover -s tests -v
The integration's pysma-plus dependency must be installed.
"""

import ast
import logging
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pysmaplus as pysma

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/pysmaplus/__init__.py"

SCAN_INTERVAL = 60
MAX_BACKOFF = timedelta(minutes=15).total_seconds()


class UpdateFailed(Exception):
    """Stand-in for HA's coordinator exception in this isolated callback test."""

    def __init__(self, *args, retry_after=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


def load_update_callback(device, access="ennexos", scan_interval=SCAN_INTERVAL):
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
    backoff = {"failures": 0, "delay": float(scan_interval)}
    namespace = {
        "pysma": pysma,
        "sma": device,
        "sensor_def": [],
        "entry": SimpleNamespace(
            data={"host": "test-inverter", "access": access, "device": "IGULD:SELF"}
        ),
        "CONF_HOST": "host",
        "CONF_ACCESS": "access",
        "CONF_DEVICE": "device",
        "_LOGGER": logging.getLogger("test.pysmaplus.coordinator"),
        "UpdateFailed": UpdateFailed,
        "interval": timedelta(seconds=scan_interval),
        # Mirrors max_backoff in async_setup_entry: 15 min, or the scan
        # interval when that is longer.
        "max_backoff": max(MAX_BACKOFF, float(scan_interval)),
        "backoff": backoff,
    }
    exec(
        compile(ast.Module(body=[callback], type_ignores=[]), str(SOURCE), "exec"),
        namespace,
    )
    return namespace["async_update_data"], backoff


class AuthenticationFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_authentication_failure_is_an_update_failure(self):
        error = pysma.exceptions.SmaAuthenticationException("HTTP 401 after retry")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await load_update_callback(device)[0]()
        self.assertIs(caught.exception.__cause__, error)
        self.assertIsNone(caught.exception.retry_after)
        device.read.assert_awaited_once()

    async def test_connection_failure_remains_an_update_failure(self):
        error = pysma.exceptions.SmaConnectionException("Disconnected")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await load_update_callback(device)[0]()
        self.assertIs(caught.exception.__cause__, error)
        self.assertIsNone(caught.exception.retry_after)

    async def test_successful_read_remains_successful(self):
        device = SimpleNamespace(read=AsyncMock(return_value=True))
        with self.assertNoLogs("test.pysmaplus.coordinator", level="WARNING"):
            self.assertIsNone(await load_update_callback(device)[0]())
        device.read.assert_awaited_once_with([], "IGULD:SELF")


class FailureBackoffTests(unittest.IsolatedAsyncioTestCase):
    """speedwireinv/speedwireinvV2 ask the coordinator to retry after a delay."""

    async def test_speedwireinv_failures_double_the_retry_delay(self):
        error = pysma.exceptions.SmaConnectionException("No Response from Device")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        update, backoff = load_update_callback(device, access="speedwireinv")
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            for expected in (60, 120, 240, 480, 900, 900):
                with self.assertRaises(UpdateFailed) as caught:
                    await update()
                self.assertEqual(caught.exception.retry_after, expected)
        self.assertEqual(backoff["failures"], 6)
        self.assertEqual(backoff["delay"], MAX_BACKOFF)
        self.assertEqual(device.read.await_count, 6)

    async def test_speedwireinvV2_uses_the_same_backoff(self):
        error = pysma.exceptions.SmaReadException("Read failed")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        update, _ = load_update_callback(device, access="speedwireinvV2")
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await update()
        self.assertEqual(caught.exception.retry_after, SCAN_INTERVAL)

    async def test_success_resets_the_backoff(self):
        error = pysma.exceptions.SmaConnectionException("No Response from Device")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        update, backoff = load_update_callback(device, access="speedwireinv")
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            for _ in range(3):
                with self.assertRaises(UpdateFailed):
                    await update()
        self.assertEqual(backoff["failures"], 3)

        device.read = AsyncMock(return_value=True)
        with self.assertLogs("test.pysmaplus.coordinator", level="INFO") as logs:
            self.assertIsNone(await update())
        self.assertTrue(
            any(
                "test-inverter/speedwireinv/IGULD:SELF: recovered after 3 consecutive failure(s)"
                in line
                for line in logs.output
            )
        )
        self.assertEqual(backoff["failures"], 0)
        self.assertEqual(backoff["delay"], SCAN_INTERVAL)

        device.read = AsyncMock(side_effect=error)
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            with self.assertRaises(UpdateFailed) as caught:
                await update()
        self.assertEqual(caught.exception.retry_after, SCAN_INTERVAL)

    async def test_backoff_never_retries_faster_than_the_scan_interval(self):
        # A scan interval above the 15 minute cap must not shrink the retry
        # delay below the normal polling cadence during failures.
        error = pysma.exceptions.SmaConnectionException("No Response from Device")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        update, backoff = load_update_callback(
            device, access="speedwireinv", scan_interval=1800
        )
        with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
            for _ in range(3):
                with self.assertRaises(UpdateFailed) as caught:
                    await update()
                self.assertEqual(caught.exception.retry_after, 1800)
        self.assertEqual(backoff["failures"], 3)
        self.assertEqual(backoff["delay"], 1800)

    async def test_backoff_survives_more_failures_than_the_old_exponent_overflow(self):
        error = pysma.exceptions.SmaConnectionException("No Response from Device")
        device = SimpleNamespace(read=AsyncMock(side_effect=error))
        update, backoff = load_update_callback(device, access="speedwireinv")
        # Muting the logger keeps 1100 exc_info tracebacks from slowing the test.
        logger = logging.getLogger("test.pysmaplus.coordinator")
        level = logger.level
        logger.setLevel(logging.CRITICAL)
        try:
            for i in range(1100):
                with self.assertRaises(UpdateFailed) as caught:
                    await update()
                expected = MAX_BACKOFF if i >= 4 else SCAN_INTERVAL * 2**i
                self.assertEqual(caught.exception.retry_after, expected)
        finally:
            logger.setLevel(level)
        self.assertEqual(backoff["failures"], 1100)
        self.assertEqual(backoff["delay"], MAX_BACKOFF)

    async def test_other_access_methods_keep_regular_polling(self):
        for access in ("webconnect", "ennexos", "speedwireem", "shm2", "speedwire"):
            with self.subTest(access=access):
                error = pysma.exceptions.SmaConnectionException("Failed")
                device = SimpleNamespace(read=AsyncMock(side_effect=error))
                update, backoff = load_update_callback(device, access=access)
                with self.assertLogs("test.pysmaplus.coordinator", level="WARNING"):
                    for _ in range(3):
                        with self.assertRaises(UpdateFailed) as caught:
                            await update()
                        self.assertIsNone(caught.exception.retry_after)
                self.assertEqual(backoff["failures"], 0)
                self.assertEqual(device.read.await_count, 3)


if __name__ == "__main__":
    unittest.main()
