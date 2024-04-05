# Generated by ariadne-codegen
# Source: queries.graphql

from typing import List, Optional

from .base_model import BaseModel
from .fragments import MarketFields


class GetMarkets(BaseModel):
    markets: List[Optional["GetMarketsMarkets"]]


class GetMarketsMarkets(MarketFields):
    pass


GetMarkets.model_rebuild()
