"""Constants for the Vestel TV integration."""
from __future__ import annotations

DOMAIN = "vestel_tv"

CONF_SOURCES = "sources"
CONF_SUPPORTS_POWER = "supports_power"

DEFAULT_NAME = "Vestel TV"
DEFAULT_SOURCES = ["TV", "HDMI1", "HDMI2", "HDMI3", "Netflix", "YouTube"]
DEFAULT_TIMEOUT = 5
DEFAULT_PORT_TCP = 1986
DEFAULT_PORT_WS = 7681
DEFAULT_SCAN_INTERVAL = 30

KEY_POWER = 1012
KEY_MUTE = 1013
KEY_VOL_UP = 1016
KEY_VOL_DOWN = 1017
KEY_PREV_TRACK = 1027
KEY_NEXT_TRACK = 1028
KEY_PROG_UP = 1032
KEY_PROG_DOWN = 1033
KEY_SOURCE = 1056

KEYS_DIGIT = {str(i): 1000 + i for i in range(10)}
