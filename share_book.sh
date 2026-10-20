#!/bin/bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <book_url> <bucket_name> <expiration_seconds>" >&2
    exit 1
fi

URL="$1"
BUCKET="$2"
EXPIRATION="$3"
FILE="$(basename "$URL")"

mkdir -p books
curl -fsS -o "books/$FILE" "$URL"

if aws s3 ls "s3://$BUCKET" > /dev/null 2>&1; then
	echo "Bucket $BUCKET already exists"
else
	aws s3 mb "s3://$BUCKET" --region us-east-1
fi

aws s3 cp "books/$FILE" "s3://$BUCKET/$FILE" \
	--content-type "text/plain; charset=utf-8"

aws s3 presign "s3://$BUCKET/$FILE" --expires-in "$EXPIRATION" --region us-east-1



