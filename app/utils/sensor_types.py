from __future__ import annotations

from enum import Enum


class SensorName(str, Enum):
    MQ135 = "mq135"
    MICS6814 = "mics6814"
    FERMION_NH3 = "fermion_nh3"
    FERMION_H2S = "fermion_h2s"


class RatioMode(str, Enum):
    RS_OVER_R0 = "rs_r0"
    R0_OVER_RS = "r0_rs"
