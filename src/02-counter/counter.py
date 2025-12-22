import boto3
import pytest

@pytest.fixture
def lambda_client():
    return boto3.client("lambda", region_name="us-east-2")
