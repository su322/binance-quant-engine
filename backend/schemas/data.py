from pydantic import BaseModel, Field
from typing import List, Optional


class DownloadRequest(BaseModel):
    symbol: str = Field(..., description="交易对，如 BTCUSDT")
    interval: str = Field(
        ...,
        description="K线周期。支持: 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo (1mo is used instead of 1M to support non-case sensitive file systems)",
    )
    start_date: str = Field(..., description="开始月份，格式 YYYY-MM，如 2024-01")
    end_date: str = Field(..., description="结束月份，格式 YYYY-MM，如 2025-12")


class FileListResponse(BaseModel):
    """
    文件列表响应模型
    """

    files: List[str] = Field(..., description="已处理的CSV文件列表")
