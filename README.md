# Hotel AWS API

FastAPI service that exposes the latest hotel GL serving file stored in S3.

This repo is one of three Docker images used in the hotel GL aggregation pipeline.  
This image provides the API layer and returns a presigned URL for the latest serving parquet file.

---

## What this API does

The API connects to S3 and exposes endpoints under `/api`.

| Endpoint | Description |
|----------|-------------|
| `/api/health` | Confirms API is running and S3 is reachable |
| `/api/ready` | Readiness check for container deployment |
| `/api/serving/latest` | Returns a presigned URL for the serving parquet file |

---

## How it works

1. Scan configured S3 prefix
2. Find `.parquet` files
3. Enforce exactly **one** parquet file exists
4. Return metadata + presigned URL (default 5 min expiry)

---

## Configuration

Configured via environment variables:

| Variable | Default | Description |
|----------|--------|-------------|
| AWS_REGION | us-east-2 | AWS region |
| S3_BUCKET | opera-hotel | S3 bucket |
| S3_PREFIX | serving/2026-04/ | Location of serving file |
| PRESIGNED_URL_EXPIRES_SECONDS | 300 | URL expiry time |

---

## Important note about local execution

This service requires AWS credentials.

Recommended:
- Run on EC2 with IAM role

Local:
- Requires AWS CLI configuration

---

## AWS credential setup (local)

Install AWS CLI:
## AWS credential setup for local testing

Install AWS CLI:

```bash
conda install -c conda-forge awscliv2
```

Configure AWS credentials:

```bash
aws configure
```

Credentials are usually stored in:

```text
C:\Users\<your-user>\.aws
```

## Run locally with Python

```bash
python main.py
```

API:

```text
http://localhost:8000
```

Docs:

```text
http://localhost:8000/docs
```

## Build Docker image

```bash
docker build -t hotel-aws-api .
docker image ls
```

## Run with Docker locally

For Git Bash on Windows:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -p 8000:8000 \
  --mount type=bind,src=/c/Users/CGao/.aws,dst=/aws,readonly \
  -e AWS_SHARED_CREDENTIALS_FILE=/aws/credentials \
  -e AWS_CONFIG_FILE=/aws/config \
  -e AWS_REGION=us-east-2 \
  -e S3_BUCKET=opera-hotel \
  -e S3_PREFIX=serving/2026-04/ \
  hotel-aws-api
```

## Example usage

Health check:

```bash
curl http://localhost:8000/api/health
```

Readiness check:

```bash
curl http://localhost:8000/api/ready
```

Get latest parquet file:

```bash
curl http://localhost:8000/api/serving/latest
```

Example response:

```json
{
  "parquet_key": "serving/2026-04/gl_summary.parquet",
  "last_modified": "2026-04-01T12:00:00+00:00",
  "presigned_url": "https://...",
  "expires_in_seconds": 300
}
```

## Run on EC2

Recommended testing flow:

1. SSH into EC2
2. Clone this repo
3. Confirm EC2 has S3 read permission
4. Build the Docker image
5. Run the container
6. Test the API endpoints

```bash
docker build -t hotel-aws-api .

docker run --rm \
  -p 8000:8000 \
  -e AWS_REGION=us-east-2 \
  -e S3_BUCKET=opera-hotel \
  -e S3_PREFIX=serving/2026-04/ \
  hotel-aws-api
```

On EC2, use the instance IAM role instead of mounting local `.aws` credentials.

## Assumptions

- Exactly one `.parquet` file exists under the configured S3 prefix
- The EC2 instance or local user has permission to read the S3 bucket
- The API currently returns a temporary presigned URL only

## Future improvements

- Select the latest parquet file instead of enforcing one file
- Add logging
- Add authentication
- Add API versioning such as `/api/v1`