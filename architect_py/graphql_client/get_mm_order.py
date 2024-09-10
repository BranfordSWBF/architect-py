# Generated by ariadne-codegen
# Source: queries.graphql

from typing import Any, Optional

from pydantic import Field

from .base_model import BaseModel
from .enums import ReferencePrice


class GetMmOrder(BaseModel):
    mm_algo_order: Optional["GetMmOrderMmAlgoOrder"] = Field(alias="mmAlgoOrder")


class GetMmOrderMmAlgoOrder(BaseModel):
    name: str
    order_id: Any = Field(alias="orderId")
    market_id: Any = Field(alias="marketId")
    quantity_buy: Any = Field(alias="quantityBuy")
    quantity_sell: Any = Field(alias="quantitySell")
    min_position: Any = Field(alias="minPosition")
    max_position: Any = Field(alias="maxPosition")
    max_improve_bbo: Any = Field(alias="maxImproveBbo")
    position_tilt: Any = Field(alias="positionTilt")
    reference_price: ReferencePrice = Field(alias="referencePrice")
    ref_dist_frac: Any = Field(alias="refDistFrac")
    tolerance_frac: Any = Field(alias="toleranceFrac")
    account: Optional[Any]


GetMmOrder.model_rebuild()