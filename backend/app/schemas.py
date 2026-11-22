from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iron_feed: Number
    silica_feed: Number
    starch_flow: Number
    amina_flow: Number
    ore_pulp_flow: Number
    ore_pulp_ph: Number
    ore_pulp_density: Number
