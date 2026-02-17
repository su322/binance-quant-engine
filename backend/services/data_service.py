import asyncio
import os
import aiohttp
import zipfile
import io
import pandas as pd
from datetime import datetime
from typing import List, Tuple, Optional
from dateutil.relativedelta import relativedelta

from backend.core.logger import get_logger

logger = get_logger("DataService")


class DataService:
    """
    数据服务
    负责下载、管理和提供历史K线数据
    """

    BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to backend/data
            self.data_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
            )
        else:
            self.data_dir = data_dir

        self.historical_dir = os.path.join(self.data_dir, "historical")
        os.makedirs(self.historical_dir, exist_ok=True)

    async def download_kline_data(
        self, symbol: str, interval: str, start_date: str, end_date: str
    ):
        """
        下载指定日期范围的K线数据 (YYYY-MM)
        并合并为一个CSV文件保存
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m")
            end = datetime.strptime(end_date, "%Y-%m")

            # 生成日期列表
            current = start
            dates = []
            while current <= end:
                dates.append(current)
                current += relativedelta(months=1)

            logger.info(
                f"Starting download for {symbol} {interval} from {start_date} to {end_date} ({len(dates)} months)"
            )

            tasks = []

            # Create a custom SSL context that disables verification (Use with caution)
            import ssl

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)

            # Use trust_env=True to respect system proxy settings (important for accessing Binance)
            async with aiohttp.ClientSession(
                connector=connector, trust_env=True
            ) as session:
                for date in dates:
                    year = date.year
                    month = date.month
                    tasks.append(
                        self._download_and_extract_month(
                            session, symbol, interval, year, month
                        )
                    )

                results = await asyncio.gather(*tasks)

            # 过滤失败的结果 (None)
            dfs = [df for df in results if df is not None]

            if not dfs:
                logger.warning(f"No data downloaded for {symbol} {interval}")
                return

            # 合并所有月份数据
            full_df = pd.concat(dfs, ignore_index=True)

            # 转换列名 (Binance K线数据没有header，手动指定)
            full_df.columns = [
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_volume",
                "count",
                "taker_buy_volume",
                "taker_buy_quote_volume",
                "ignore",
            ]

            # 转换时间戳为 datetime 对象 (可选，或者保持毫秒时间戳)
            # full_df["open_time"] = pd.to_datetime(full_df["open_time"], unit='ms')
            # full_df["close_time"] = pd.to_datetime(full_df["close_time"], unit='ms')

            # 按时间排序
            full_df.sort_values("open_time", inplace=True)

            # 生成文件名: {symbol}-{interval}-{start}-{end}.csv
            filename = f"{symbol}-{interval}-{start_date}-{end_date}.csv"
            output_path = os.path.join(self.historical_dir, filename)

            full_df.to_csv(output_path, index=False)
            logger.info(f"Successfully saved merged data to {output_path}")

        except Exception as e:
            logger.error(f"Error in download_kline_data: {e}")

    async def _download_and_extract_month(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        interval: str,
        year: int,
        month: int,
    ) -> Optional[pd.DataFrame]:
        """
        下载单个月份的 zip 并提取为 DataFrame
        """
        month_str = f"{month:02d}"
        filename = f"{symbol}-{interval}-{year}-{month_str}.zip"
        url = f"{self.BASE_URL}/{symbol}/{interval}/{filename}"

        try:
            # Add timeout to prevent hanging
            timeout = aiohttp.ClientTimeout(total=60)
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    content = await response.read()

                    with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
                        # 假设 zip 中只有一个 csv 文件
                        csv_name = zip_ref.namelist()[0]
                        with zip_ref.open(csv_name) as f:
                            df = pd.read_csv(f, header=None)
                            return df
                else:
                    logger.warning(
                        f"Failed to download {url}: Status {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None

    def get_historical_files(self) -> List[str]:
        """
        获取所有已下载的历史数据文件列表
        """
        try:
            if not os.path.exists(self.historical_dir):
                return []
            files = [f for f in os.listdir(self.historical_dir) if f.endswith(".csv")]
            return sorted(files)
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []


# 单例实例
data_service = DataService()
