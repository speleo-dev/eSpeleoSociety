import os


def make_gcs_upload_blob(get_secret):
    def upload_blob(blob_name: str, data: bytes, content_type: str) -> str:
        credentials_json = get_secret("credentials_json")
        project_id = get_secret("project_id")
        bucket_name = get_secret("bucket_name")
        if not all([credentials_json, project_id, bucket_name]):
            raise RuntimeError("GCS config missing: credentials_json, project_id, or bucket_name.")

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_json
        from google.cloud import storage

        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(data, content_type=content_type)
        blob.make_public()
        return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

    return upload_blob
