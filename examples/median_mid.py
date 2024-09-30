import asyncio
from uuid import UUID
from typing import Dict, NamedTuple, Set
from statistics import median
from dataclasses import dataclass
import time
import logging
import argparse
import redis

from architect_py.async_client import AsyncClient
from architect_py.protocol.marketdata import (
    JsonMarketdataStub,
    SubscribeL1BookSnapshotsRequest,
)
from .common import create_async_client
from architect_py.async_graphql_client.search_markets import (
    SearchMarketsFilterMarkets,
)

# referenced from examples/stream_l1_marketdata.py
# python -m  examples.median_mid --log-level INFO|WARNING

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Redis setup
redis_client = redis.Redis(host="localhost", port=6379, db=0)

SUPPORTED_COINS = [
    "BTC",
    "ETH",
    "SOL",
    "SUI",
    "TIA",
    "SEI",
    "LINK",
    "DOGE",
    "WIF",
    "TON",
    "TRX",
    "SHIB",
    "AVAX",
    "DOT",
]


class MarketKey(NamedTuple):
    venue: str
    normalized_market: str


@dataclass
class VenueConfig:
    name: str
    domain: str


@dataclass
class PriceData:
    venue: str
    market: str
    normalized_market: str
    bid: float
    ask: float
    mid: float
    timestamp: float


def calculate_weighted_mid(best_bid, best_ask):
    bid_price, bid_size = float(best_bid[0]), float(best_bid[1])
    ask_price, ask_size = float(best_ask[0]), float(best_ask[1])
    total_size = bid_size + ask_size
    weighted_mid = (bid_price * ask_size + ask_price * bid_size) / total_size
    return weighted_mid


async def subscribe_to_l1_feed(
    client: AsyncClient,
    venue_config: VenueConfig,
    markets_by_id: Dict[UUID, SearchMarketsFilterMarkets],
    latest_price_by_market: Dict[MarketKey, PriceData],
    updated_markets: Set[str],
):
    channel = await client.grpc_channel(venue_config.domain)
    stub = JsonMarketdataStub(channel)
    req = SubscribeL1BookSnapshotsRequest(market_ids=None)

    logger.info(f"Starting subscription for {venue_config.name}")
    async for snap in stub.SubscribeL1BookSnapshots(req):
        if snap.market_id in markets_by_id:
            market = markets_by_id[snap.market_id]
            market_name_upper = market.name.upper()
            coin_name = market.name.split("-")[0]
            # andrew will add an accessor for grabbing base name (e.g. "ETH-USDT Perpetual")
            if not (
                coin_name in SUPPORTED_COINS or "PERPETUAL" in market_name_upper
            ):
                continue
            if snap.best_bid and snap.best_ask:
                bid = float(snap.best_bid[0])
                ask = float(snap.best_ask[0])
                weighted_mid = calculate_weighted_mid(
                    snap.best_bid, snap.best_ask
                )
                timestamp = time.time()
                normalized_market_name = f"{coin_name}-USDT-PERPETUAL"
                price_data = PriceData(
                    venue_config.name,
                    market.name,
                    normalized_market_name,
                    bid,
                    ask,
                    weighted_mid,
                    timestamp,
                )
                latest_price_by_market[
                    MarketKey(venue_config.name, normalized_market_name)
                ] = price_data
                updated_markets.add(normalized_market_name)
                logger.debug(
                    f"Updated {coin_name} data for {venue_config.name}. Weighted Mid: {weighted_mid}"
                )


def check_for_old_data(price_data: PriceData, current_time: float):
    age = current_time - price_data.timestamp
    if age > 0.05:
        logger.warning(
            f"Old data detected for {price_data.normalized_market} from {price_data.venue}. Age: {age:.3f}s"
        )


def print_results(
    normalized_market: str,
    median_weighted_mid: float,
    latest_price_by_market: Dict[MarketKey, PriceData],
    current_time: float,
):
    logger.info(f"\nNormalized Market: {normalized_market}")
    logger.info(f"Median weighted mid-price: {median_weighted_mid}")
    logger.info("Venue data:")
    for (venue, market), data in latest_price_by_market.items():
        if market == normalized_market:
            age = current_time - data.timestamp
            logger.info(
                f"  {venue} ({data.market}): Bid: {data.bid}, Ask: {data.ask}, Weighted Mid: {data.mid}, Age: {age:.3f}s"
            )
    logger.info("-" * 40)


async def bulk_redis_update(
    latest_price_by_market: Dict[MarketKey, PriceData],
    updated_markets: Set[str],
):
    pipe = redis_client.pipeline()
    for normalized_market in updated_markets:
        relevant_data = [
            data
            for (venue, market), data in latest_price_by_market.items()
            if market == normalized_market
        ]
        weighted_mids = [data.mid for data in relevant_data]
        median_weighted_mid = median(weighted_mids)

        redis_key = f"{normalized_market}#latest_value"
        pipe.set(redis_key, str(median_weighted_mid))

        logger.info(
            f"Calculated median weighted mid-price for {normalized_market}: {median_weighted_mid}"
        )

        current_time = time.time()
        for data in relevant_data:
            check_for_old_data(data, current_time)

        print_results(
            normalized_market,
            median_weighted_mid,
            latest_price_by_market,
            current_time,
        )

    pipe.execute()
    logger.info(f"Bulk updated Redis for {len(updated_markets)} markets")
    updated_markets.clear()


async def periodic_redis_update(
    latest_price_by_market: Dict[MarketKey, PriceData],
    updated_markets: Set[str],
):
    while True:
        await asyncio.sleep(0.1)  # Sleep for 0.1 seconds
        if updated_markets:
            await bulk_redis_update(latest_price_by_market, updated_markets)


async def main(log_level):
    logging.getLogger().setLevel(log_level)

    client: AsyncClient = create_async_client()

    venue_configs = [
        VenueConfig("BYBIT", "bybit.marketdata.architect.co"),
        VenueConfig("OKX", "okx.marketdata.architect.co"),
        VenueConfig(
            "BINANCE-FUTURES-USD-M",
            "binance-futures-usd-m.marketdata.architect.co",
        ),
    ]

    markets_by_id: Dict[UUID, SearchMarketsFilterMarkets] = {}
    for config in venue_configs:
        logger.info(f"Searching markets for {config.name}")
        search_markets = await client.search_markets(venue=config.name)
        for market in search_markets:
            markets_by_id[UUID(market.id)] = market

    logger.info(
        f"Loaded {len(markets_by_id)} perpetual markets for {', '.join(SUPPORTED_COINS)}"
    )

    latest_price_by_market: Dict[MarketKey, PriceData] = {}
    updated_markets: Set[str] = set()

    logger.info("Starting subscription tasks and periodic Redis update")
    tasks = [
        subscribe_to_l1_feed(
            client,
            config,
            markets_by_id,
            latest_price_by_market,
            updated_markets,
        )
        for config in venue_configs
    ]
    tasks.append(periodic_redis_update(latest_price_by_market, updated_markets))

    logger.info("Awaiting tasks")
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the market data processor."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    asyncio.run(main(log_level))
