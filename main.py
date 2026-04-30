import os
import boto3
import uvicorn
from botocore.config import Config
from fastapi import APIRouter, FastAPI, HTTPException


AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET", "opera-hotel")
S3_PREFIX = os.getenv("S3_PREFIX", "serving/2026-04/")
PRESIGNED_URL_EXPIRES_SECONDS = int(
    os.getenv("PRESIGNED_URL_EXPIRES_SECONDS", "300")
)

app = FastAPI(
    title="Hotel AWS API",
    description="API for exposing the latest hotel GL serving parquet file from S3.",
    version="0.1.0",
)

router = APIRouter(prefix="/api")

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(signature_version="s3v4"),
)


def check_s3_access() -> None:
    """Lightweight check that confirms the configured S3 prefix is reachable."""
    s3.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=S3_PREFIX,
        MaxKeys=1,
    )


def get_parquet_files() -> list[dict]:
    """Return parquet files under the configured S3 prefix."""
    response = s3.list_objects_v2(
        Bucket=S3_BUCKET,
        Prefix=S3_PREFIX,
    )

    contents = response.get("Contents", [])

    return [
        obj
        for obj in contents
        if obj["Key"].endswith(".parquet")
    ]


@router.get("/health")
def health_check():
    try:
        check_s3_access()
        return {
            "status": "ok",
            "s3": "reachable",
            "bucket": S3_BUCKET,
            "prefix": S3_PREFIX,
            "region": AWS_REGION,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {exc}",
        ) from exc


@router.get("/ready")
def ready_check():
    try:
        check_s3_access()
        return {
            "status": "ready",
            "s3": "ok",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Readiness check failed: {exc}",
        ) from exc


@router.get("/serving/latest")
def get_latest_serving_parquet():
    try:
        parquet_files = get_parquet_files()

        if not parquet_files:
            raise HTTPException(
                status_code=404,
                detail="No parquet files found in the configured S3 bucket and prefix.",
            )

        if len(parquet_files) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Multiple parquet files found under the configured prefix. "
                    "Please keep only one serving parquet file or update the API logic."
                ),
            )

        parquet_file = parquet_files[0]
        parquet_key = parquet_file["Key"]

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": parquet_key,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRES_SECONDS,
        )

        return {
            "parquet_key": parquet_key,
            "last_modified": parquet_file["LastModified"].isoformat(),
            "presigned_url": presigned_url,
            "expires_in_seconds": PRESIGNED_URL_EXPIRES_SECONDS,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get latest serving parquet file: {exc}",
        ) from exc


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )