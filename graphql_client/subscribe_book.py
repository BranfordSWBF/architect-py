# Generated by ariadne-codegen
# Source: queries.graphql

from typing import Any, List

from .base_model import BaseModel


class SubscribeBook(BaseModel):
    book: "SubscribeBookBook"


class SubscribeBookBook(BaseModel):
    bids: List["SubscribeBookBookBids"]
    asks: List["SubscribeBookBookAsks"]


class SubscribeBookBookBids(BaseModel):
    price: Any
    amount: Any
    total: Any


class SubscribeBookBookAsks(BaseModel):
    price: Any
    amount: Any
    total: Any


SubscribeBook.model_rebuild()
SubscribeBookBook.model_rebuild()