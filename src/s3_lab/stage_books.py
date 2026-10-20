#!/usr/bin/env python3
import json
import sys
import time
import logging
import os
import requests
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

s3 = boto3.client("s3", region_name="us-east-1")

def parse_args():
	'''Return tuple of command line arguements'''
	if len(sys.argv) < 4:
		log.error("Too many arguements")
		sys.exit(1)
	return (sys.argv[1], sys.argv[2], sys.argv[3])

def download_books(list_file, dest_dir):
	'''Read the path of the book list and destination directory, and return a list of local paths of the books'''
	os.makedirs(dest_dir, exist_ok=True)
	with open(list_file) as f:
		urls_list = [line.strip() for line in f if line.strip()]
	paths = []
	for url in urls_list:
		path = os.path.join(dest_dir, os.path.basename(url))
		if not os.path.exists(path):
			try:
				response = requests.get(url, timeout=30)
				response.raise_for_status() 
				with open(path, "wb") as out:
					out.write(response.content)
				log.info(f"Downloaded {url} to {path}")
			except requests.RequestException as e:
				log.error(f"Error downloading {url}: {e}")
				continue
			time.sleep(1)
		paths.append(path)
	return paths

def create_bucket(bucket):
	'''Create bucket, return True if successful and false if not'''
	try:
		s3.head_bucket(Bucket=bucket)
		log.info(f"Bucket {bucket} already exists")
		return True
	except ClientError:
		log.info(f"Bucket {bucket} not found, initiating creation")
	try:
		s3.create_bucket(Bucket=bucket)
		log.info(f"Created bucket {bucket}")
		return True
	except ClientError as e:
		log.error(f"Error creating bucket {bucket}: {e}")
		return False

def make_public(bucket):
	''' Turn off Block Public Access for the bucket, then attach a bucket policy that allows anyone to read its objects '''
	
	policy = {
		"Version": "2012-10-17",
		"Statement": [
			{
			"Effect": "Allow",
			"Principal": "*",
			"Action": "s3:GetObject",
			"Resource": "arn:aws:s3:::public-bvc9xp/*"
			}
		]
	}
	try:
		s3.put_public_access_block(
			Bucket=bucket,
			PublicAccessBlockConfiguration={
				"BlockPublicAcls": False,
				"IgnorePublicAcls": False,
				"BlockPublicPolicy": False,
				"RestrictPublicBuckets": False,
				},
			)
		
		log.info(f"Turned off Public Access for {bucket}")
		
		s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
		log.info(f"Attached policy to {bucket}")
		
		return True
	except ClientError as e:
		log.error(f"Error making bucket {bucket} public: {e}")
		return False

def upload_files(bucket, file_paths):

	'''takes in bucket and file paths and returns number of files uploaded successfully'''
	count = 0
	for i in file_paths:
		key = os.path.basename(i)
		try:
			with open(i, "rb") as f:
				s3.put_object(
					Bucket=bucket,
					Key=key,
					Body=f,
					ContentType="text/plain; charset=utf-8",)
			log.info(f"Uploaded {i} to s3://{bucket}/{key}")
			count +=1
		except FileNotFoundError:
			log.error(f"Local file not found: {i}")
		except ClientError as e:
			log.error(f"Error uploading {i}: {e}")
	return count

def upload_index(bucket, index_path):

	'''Takes in bucket and index path from command line and uploads file with key index.html and ContentType="text/html"'''

	try:
		with open(index_path, "rb") as f:
			s3.put_object(
				Bucket=bucket,
				Key="index.html",
				Body = f,
				ContentType="text/html",)
		log.info(f'Uploaded content to bucket')
		return True
	except FileNotFoundError:
		log.error(f"Local file not found: {index_path}")
		return False
	except ClientError as e:
		log.error(f"Error uploading {index_path}: {e}")
		return False

def main():
	list_file, index_path, bucket = parse_args()
	paths = download_books(list_file, "books")
	if not paths:
		log.error("Download failed")
		sys.exit(1)
	if not create_bucket(bucket):
		sys.exit(1)
	if not make_public(bucket):
		sys.exit(1)
	uploaded = upload_files(bucket, paths)
	index_temp = upload_index(bucket, index_path)
	
	if uploaded == len(paths) and index_temp:
		log.info("Successful upload")
	else:
		log.error("Failed")

if __name__ == "__main__":
	main()
