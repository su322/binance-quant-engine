import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.services.data_service import data_service


async def test_download():
    # Try to download 1 month of data (Jan 2024, likely exists)
    print("Testing download...")
    await data_service.download_kline_data(
        symbol="BTCUSDT", interval="1m", start_date="2024-01", end_date="2024-01"
    )
    print("Download finished.")


if __name__ == "__main__":
    asyncio.run(test_download())
