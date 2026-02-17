from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.schemas.data import DownloadRequest, FileListResponse
from backend.schemas.response import StandardResponse
from backend.services.data_service import data_service
from backend.core.logger import get_logger

router = APIRouter(prefix="/data", tags=["data"])

logger = get_logger("DataRouter")


@router.post("/klines/download", response_model=StandardResponse[dict])
async def download_klines_data(
    request: DownloadRequest, background_tasks: BackgroundTasks
):
    """
    下载历史K线数据 (支持日期范围 YYYY-MM)
    """
    try:
        logger.info(
            f"Received download request: {request.symbol} {request.interval} ({request.start_date}-{request.end_date})"
        )

        background_tasks.add_task(
            data_service.download_kline_data,
            request.symbol,
            request.interval,
            request.start_date,
            request.end_date,
        )

        return StandardResponse(
            message=f"Started downloading klines data for {request.symbol} from {request.start_date} to {request.end_date}.",
            data={
                "symbol": request.symbol,
                "interval": request.interval,
                "range": f"{request.start_date} to {request.end_date}",
            },
        )
    except Exception as e:
        logger.error(f"Failed to start download task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/klines/files", response_model=StandardResponse[FileListResponse])
async def list_klines_files():
    """
    列出已下载的历史K线数据文件
    """
    try:
        files = data_service.get_historical_files()
        logger.info(f"Listed {len(files)} historical klines files")
        return StandardResponse(data=FileListResponse(files=files))
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
