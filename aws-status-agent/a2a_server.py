import logging, os, json, datetime
from strands import Agent, tool
from strands.models import BedrockModel
from strands.multiagent.a2a import A2AServer
from fastapi import FastAPI
import uvicorn, boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')

@tool
def aws_resource_check(resource: str) -> str:
    """Return the status of an AWS resource for the lab.

    Args:
        resource: Name of the AWS resource to check.
    Returns:
        A short status string.
    """
    return f"AWS resource '{resource}': healthy."

@tool
def deploy_status_api(bucket_name: str) -> str:
    """Deploy the AWS status API: an S3 static website serving status.json,
    using the AgentCore execution role's credentials.

    Args:
        bucket_name: Globally-unique S3 bucket name, e.g. 'txlab-dev-status-<initials>'.
    Returns:
        The public URL of status.json.
    """
    region = os.environ.get("AWS_REGION", "us-east-1")
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.create_bucket(Bucket=bucket_name)  # us-east-1: no LocationConstraint
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            return f"Failed to create bucket: {e.response['Error']['Code']}"
    body = json.dumps({"component": "aws-status-api", "status": "healthy",
                       "deployed_at": datetime.datetime.utcnow().isoformat() + "Z"})
    s3.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={
        "BlockPublicAcls": False, "IgnorePublicAcls": False,
        "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps({
        "Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": "*",
        "Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{bucket_name}/*"}]}))
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration={"CORSRules": [
        {"AllowedMethods": ["GET"], "AllowedOrigins": ["*"], "AllowedHeaders": ["*"]}]})
    s3.put_object(Bucket=bucket_name, Key="status.json", Body=body.encode(),
                  ContentType="application/json")
    s3.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration={
        "IndexDocument": {"Suffix": "status.json"}})
    url = f"http://{bucket_name}.s3-website-{region}.amazonaws.com/status.json"
    return f"AWS status API deployed. status.json URL: {url}"

model = BedrockModel(model_id="us.amazon.nova-lite-v1:0", region_name="us-east-1")
agent = Agent(model=model, name='InfraAgent', callback_handler=None,
              description='AWS-side infra agent for the multi-cloud lab.',
              tools=[aws_resource_check, deploy_status_api])
server = A2AServer(agent=agent, http_url=runtime_url, serve_at_root=True)
app = FastAPI()

@app.get('/ping')
def ping(): return {'status': 'healthy'}

app.mount('/', server.to_fastapi_app())

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=9000)

