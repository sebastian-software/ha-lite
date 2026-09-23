"""Automatically generated file.

To update, run python3 -m script.hassfest
"""

from typing import Final

MQTT: Final[dict[str, list[str]]] = {
    "drop_connect": [
        "drop_connect/discovery/#",
    ],
    "dsmr_reader": [
        "dsmr/#",
    ],
    "fully_kiosk": [
        "fully/deviceInfo/+",
    ],
    "greencell": [
        "/greencell/broadcast/device",
    ],
    "inels": [
        "inels/status/#",
    ],
    "pglab": [
        "pglab/discovery/#",
    ],
    "qbus": [
        "cloudapp/QBUSMQTTGW/state",
        "cloudapp/QBUSMQTTGW/config",
        "cloudapp/QBUSMQTTGW/+/state",
    ],
    "silla_prism": [
        "prism/hello",
    ],
    "tasmota": [
        "tasmota/discovery/#",
    ],
}
