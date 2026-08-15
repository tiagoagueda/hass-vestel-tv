"""Constants for the Vestel TV integration."""
from __future__ import annotations

DOMAIN = "vestel_tv"

CONF_SOURCES = "sources"
CONF_SUPPORTS_POWER = "supports_power"

DEFAULT_NAME = "Vestel TV"
DEFAULT_SOURCES = ["TV", "HDMI1", "HDMI2", "HDMI3", "Netflix", "YouTube"]
DEFAULT_TIMEOUT = 5
DEFAULT_PORT_WS = 7681
DEFAULT_SCAN_INTERVAL = 30

# Where a TV's DIAL description (dd.xml) tends to live, most likely first. SSDP
# is authoritative, but probing these answers a config-flow form far quicker
# than waiting for a discovery round.
DESCRIPTION_PORTS = (56790, 56789, 8080, 1900)

# The SSDP search target Vestel's own app uses to find its TVs.
SSDP_SEARCH_TARGET = "urn:dial-multiscreen-org:service:dial:1"
SSDP_DEVICE_TYPE = "urn:schemas-upnp-org:device:tvdevice:1"

# Commands POST to this DIAL app endpoint, relative to the discovered
# Application-URL, and the TV answers 201 Created. The header and charset below
# are what Vestel's own app sends; the TV is picky about the header.
SMARTCENTER_APP = "SmartCenter"
APP_NAME_HEADER = "application_name"
APP_NAME_VALUE = "tv smart centre"
CONTENT_TYPE = "text/plain; charset=ISO-8859-1"
PAYLOAD_ENCODING = "iso-8859-1"

# Query commands the TV understands. Replies arrive on the WebSocket, never in
# the POST response body.
COMMAND_TV_STATE = "tvstate"
COMMAND_VOLUME = "volume"
COMMAND_PROGRAM = "program"
COMMAND_CHANNEL_LIST = "activechannellist"
COMMAND_APP_LIST = "getapplicationlist"
COMMAND_LAUNCHER_APP_LIST = "getlauncherapplist"
COMMAND_PORTAL_URL = "getportalurl"
COMMAND_SPECIAL_PORTAL_APPS = "specialportalapps"
COMMAND_TIMER_LIST = "timerlist"
COMMAND_RECORD_LIST = "recordlist"
COMMAND_CLOSE_ALL_APPS = "closeallapps"
COMMAND_START_FOLLOW_TV = "startfollowtv"

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
