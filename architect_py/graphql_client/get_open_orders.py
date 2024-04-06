# Generated by ariadne-codegen
# Source: queries.graphql

from typing import List

from pydantic import Field

from .base_model import BaseModel
from .fragments import OrderLogFields


class GetOpenOrders(BaseModel):
    open_orders: List["GetOpenOrdersOpenOrders"] = Field(alias="openOrders")


class GetOpenOrdersOpenOrders(OrderLogFields):
    pass


GetOpenOrders.model_rebuild()