"""Delete R2 objects for specific repos (or all). Usage: python reset_r2.py [owner/repo ...]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os


def load_env(path: str = ".env.local") -> None:
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


load_env()

from src.config import GCP_PROJECT, R2_BUCKET
from src.secrets import get_secret
from src.store import get_s3_client

s3 = get_s3_client(
    access_key=get_secret(GCP_PROJECT, "R2_ACCESS_KEY_ID"),
    secret_key=get_secret(GCP_PROJECT, "R2_SECRET_ACCESS_KEY"),
    account_id=get_secret(GCP_PROJECT, "R2_ACCOUNT_ID"),
)

# Filter by repo if passed as args e.g. "duckdb/dbt-duckdb"
filters = sys.argv[1:]  # e.g. ["duckdb/dbt-duckdb"]

paginator = s3.get_paginator("list_objects_v2")
keys = []
for page in paginator.paginate(Bucket=R2_BUCKET):
    for obj in page.get("Contents", []):
        key = obj["Key"]
        if not filters or any(f in key for f in filters):
            keys.append({"Key": key})

if not keys:
    print("Nothing to delete.")
    sys.exit(0)

print(f"Deleting {len(keys)} objects{f' for {filters}' if filters else ''}...")
for k in keys:
    print(f"  {k['Key']}")

for i in range(0, len(keys), 1000):
    s3.delete_objects(Bucket=R2_BUCKET, Delete={"Objects": keys[i:i+1000]})

print("Done.")
