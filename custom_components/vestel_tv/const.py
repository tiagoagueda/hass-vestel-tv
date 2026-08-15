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

# Remote key codes. 1012/1013/1016/1017 and the digits are confirmed against a
# real TV; 1010 (back) and 1037 (exit) were seen in a capture of Vestel's own
# app. The rest come from hyttysmyrkky/node-red-contrib-vestel-tv and are
# consistent with those, but are otherwise unverified here.
KEY_POWER = 1012
KEY_MUTE = 1013
KEY_VOL_UP = 1016
KEY_VOL_DOWN = 1017
KEY_SOURCE = 1056

KEY_BACK = 1010
KEY_EXIT = 1037
KEY_MENU = 1048
KEY_QUICK_MENU = 1043
KEY_APP = 1046
KEY_OK = 1053
KEY_UP = 1020
KEY_DOWN = 1019
KEY_LEFT = 1021
KEY_RIGHT = 1022

KEY_INFO = 1018
KEY_EPG = 1047
KEY_TEXT = 1255
KEY_TEXT2 = 1060
KEY_SUBTITLE = 1031
KEY_LANGUAGE = 1015
KEY_ASPECT_RATIO = 1011
KEY_FAVORITES = 1040
KEY_SLEEP_TIMER = 1042

KEY_PROG_UP = 1032
KEY_PROG_DOWN = 1033
KEY_PROG_PREVIOUS = 1034

KEY_PLAY = 1025
KEY_PAUSE = 1049
KEY_STOP = 1024
KEY_RECORD = 1051
KEY_REWIND = 1027
KEY_FORWARD = 1028
# Kept as aliases: the media player maps prev/next track onto these.
KEY_PREV_TRACK = KEY_REWIND
KEY_NEXT_TRACK = KEY_FORWARD

KEY_RED = 1055
KEY_GREEN = 1054
KEY_YELLOW = 1050
KEY_BLUE = 1052

KEY_NETFLIX = 1064
KEY_WEB_BROWSER = 1065
KEY_MEDIA_BROWSER = 1057
KEY_RECORDINGS = 1059
KEY_SETTINGS = 1067

KEYS_DIGIT = {str(i): 1000 + i for i in range(10)}

# Buttons exposed as their own entities: (key suffix, translation key, code).
REMOTE_BUTTONS: tuple[tuple[str, int], ...] = (
    ("up", KEY_UP),
    ("down", KEY_DOWN),
    ("left", KEY_LEFT),
    ("right", KEY_RIGHT),
    ("ok", KEY_OK),
    ("back", KEY_BACK),
    ("exit", KEY_EXIT),
    ("menu", KEY_MENU),
    ("quick_menu", KEY_QUICK_MENU),
    ("apps", KEY_APP),
    ("info", KEY_INFO),
    ("epg", KEY_EPG),
    ("text", KEY_TEXT),
    ("subtitle", KEY_SUBTITLE),
    ("channel_up", KEY_PROG_UP),
    ("channel_down", KEY_PROG_DOWN),
    ("source", KEY_SOURCE),
)
