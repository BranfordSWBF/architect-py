import redis
import time
from typing import Dict
import asyncio

# List of supported coins (make sure this matches the list in your main script)
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

# Redis connection setup
redis_client = redis.Redis(host="localhost", port=6379, db=0)


async def read_prices():
    while True:
        prices: Dict[str, float] = {}
        current_time = time.time()

        for coin in SUPPORTED_COINS:
            key = f"{coin}-USDT-PERPETUAL#latest_value"
            value = redis_client.get(key)
            if value:
                prices[coin] = float(value)

        # Clear the console (works on most terminals)
        print("\033c", end="")

        print(f"Latest Mid-Prices (as of {time.strftime('%Y-%m-%d %H:%M:%S')})")
        print("=" * 50)
        for coin, price in prices.items():
            print(f"{coin:<5}: {price:,.6f} USDT")
        print("=" * 50)

        # Wait for 1 second before the next update
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(read_prices())
    except KeyboardInterrupt:
        print("\nStopping price reader.")
