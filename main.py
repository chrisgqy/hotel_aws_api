from fastapi import FastAPI, HTTPException
import boto3
from botocore.config import Config


app = FastAPI()
# s3 = boto3.client("s3")
s3 = boto3.client(
    "s3",
    region_name="us-east-2",
    config=Config(signature_version="s3v4")
)

BUCKET = "opera-hotel"
PREFIX = "serving/2026-04/"

@app.get("/health")
def health_check():
    try:
        # lightweight S3 check (doesn't list full contents)
        s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX, MaxKeys=1)

        return {
            "status": "ok",
            "s3": "reachable"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/ready")
def ready_check():
    try:
        s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX, MaxKeys=1)
        return {"status": "ready", "s3": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/serving/latest")
def get_serving_parquet():
    try:
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
        contents = resp.get("Contents", [])

        if not contents:
            raise HTTPException(
                status_code=404,
                detail="No files found in the specified S3 bucket and prefix."
            )

        parquet_files = [obj for obj in contents if obj["Key"].endswith(".parquet")]

        if not parquet_files:
            raise HTTPException(
                status_code=404,
                detail="No parquet files found in the specified S3 bucket and prefix."
            )

        if len(parquet_files) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple parquet files found. Please contact the administrator."
            )

        parquet_file = parquet_files[0]
        parquet_key = parquet_file["Key"]

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": parquet_key},
            ExpiresIn=300
        )

        return {
            "parquet_key": parquet_key,
            "last_modified": parquet_file["LastModified"].isoformat(),
            "presigned_url": presigned_url
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))