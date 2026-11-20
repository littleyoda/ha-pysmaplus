"""Check that each sensor's unit is valid for its device class.

Run with: python -m unittest discover -s tests -v
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/pysmaplus/sensor.py"

# Units Home Assistant accepts for the device classes used in sensor.py.
# None means no unit.
ALLOWED_UNITS = {
    "SensorDeviceClass.APPARENT_POWER": ("UnitOfApparentPower.",),
    "SensorDeviceClass.BATTERY": ("PERCENTAGE",),
    "SensorDeviceClass.CURRENT": ("UnitOfElectricCurrent.",),
    "SensorDeviceClass.ENERGY": ("UnitOfEnergy.",),
    "SensorDeviceClass.FREQUENCY": ("UnitOfFrequency.",),
    "SensorDeviceClass.POWER": ("UnitOfPower.",),
    "SensorDeviceClass.POWER_FACTOR": ("PERCENTAGE", None),
    "SensorDeviceClass.REACTIVE_POWER": ("UnitOfReactivePower.",),
    "SensorDeviceClass.TEMPERATURE": ("UnitOfTemperature.",),
    "SensorDeviceClass.VOLTAGE": ("UnitOfElectricPotential.",),
}


def load_descriptions():
    """Return (key, unit, device_class) for each entry of SENSOR_ENTITIES."""
    tree = ast.parse(SOURCE.read_text())
    entities = next(
        node.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign) and node.target.id == "SENSOR_ENTITIES"
    )
    for key, call in zip(entities.keys, entities.values):
        args = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}
        yield (
            ast.literal_eval(key),
            args.get("native_unit_of_measurement"),
            args.get("device_class"),
        )


def unit_allowed(unit, allowed):
    for prefix in allowed:
        if prefix is None:
            if unit is None:
                return True
        elif unit is not None and (unit == prefix or unit.startswith(prefix)):
            return True
    return False


class SensorUnitTests(unittest.TestCase):
    def test_units_match_device_class(self):
        for key, unit, device_class in load_descriptions():
            if device_class is None:
                continue
            with self.subTest(sensor=key):
                self.assertIn(device_class, ALLOWED_UNITS)
                self.assertTrue(
                    unit_allowed(unit, ALLOWED_UNITS[device_class]),
                    f"{unit} is not a valid unit for {device_class}",
                )


if __name__ == "__main__":
    unittest.main()
