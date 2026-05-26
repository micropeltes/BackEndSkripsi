from __future__ import annotations

from enum import Enum


class SensorName(str, Enum):
    MQ135 = "mq135"

    NH3_MICS = "nh3_mics"
    CO = "co"
    NO2 = "no2"

    FERMION_NH3 = "nh3_mems"
    FERMION_H2S = "h2s"


class RatioMode(str, Enum):
    RS_OVER_R0 = "rs_r0"
    R0_OVER_RS = "r0_rs"
