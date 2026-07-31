# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Schuberg Philis / Lab271
from datetime import timedelta

DOMAIN = "midas_osc"

PLATFORMS = ["number"]

# Connection (entry.data)
CONF_LOCAL_PORT = "local_port"

DEFAULT_MIXER_PORT = 10023
DEFAULT_LOCAL_PORT = 10024

# Topology (entry.options)
CONF_OUTPUTS = "outputs"
CONF_INPUTS = "inputs"
CONF_OUTPUT_DEFAULT = "output_default"

CONF_ID = "id"
CONF_LABEL = "label"
CONF_DCA = "dca"
CONF_BUS = "bus"
CONF_CH_L = "ch_l"
CONF_CH_R = "ch_r"
CONF_DEFAULT = "default"

# Flow-only field: "add another one after this"
CONF_ADD_ANOTHER = "add_another"

DEFAULT_SEND_LEVEL = 0.75
DEFAULT_FADER_LEVEL = 0.35

# The M32 accepts DCAs 1-16, input channels 1-32 and mix buses 1-16.
MAX_DCA = 16
MAX_CHANNEL = 32
MAX_BUS = 16

# /xremote subscriptions expire after ~10s, so re-arm well inside that.
REFRESH_INTERVAL = timedelta(seconds=8)

# Channel and bus numbers are zero-padded to two digits: /ch/09/mix/01/level
FADER_PATH = "/dca/{dca}/fader"
SEND_PATH = "/ch/{ch:02d}/mix/{bus:02d}/level"
