from typing import Annotated
import ibm_boto3
from ibm_botocore.client import Config as IBMConfig
from pydantic import Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType
from ibm_watsonx_orchestrate.run import connections

CLOUD_CREDS = "cloud_creds"

INDEX_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>Multi-Cloud Status Dashboard</title>
<style>body{font-family:sans-serif;background:#0a1929;color:#fff;display:grid;place-items:center;height:100vh;margin:0}
.card{background:#10243d;padding:2rem 3rem;border-radius:12px;text-align:center}
.ok{color:#42be65}.bad{color:#da1e28}h1{font-size:1.4rem}</style></head><body>
<div class="card"><h1>Multi-Cloud Status Dashboard</h1>
<p>Frontend: <span class="ok">IBM Cloud (COS static site)</span></p>
<p>AWS component: <span id="aws">checking...</span></p></div>
<script>
fetch("__AWS_STATUS_URL__").then(r=>r.json()).then(d=>{
 document.getElementById("aws").innerHTML='<span class="ok">'+d.status+' - deployed '+d.deployed_at+'</span>';
}).catch(e=>{document.getElementById("aws").innerHTML='<span class="bad">unreachable</span>';});
</script></body></html>"""

@tool(name="deploy_frontend", permission=ToolPermission.READ_WRITE,
      description="Deploy the dashboard frontend to an IBM COS static website. Deploys immediately; report result.",
      expected_credentials=[{"app_id": CLOUD_CREDS, "type": ConnectionType.KEY_VALUE}])
def deploy_frontend(
    bucket_name: Annotated[str, Field(description="COS bucket name, e.g. 'txlab-dev-dashboard-<initials>'.")],
    aws_status_url: Annotated[str, Field(description="Public URL of the AWS status.json (from the AWS agent).")],
) -> str:
    """Create/refresh the IBM COS bucket, upload the dashboard wired to the AWS
    status URL, and enable static website hosting.
    """
    c = connections.key_value(CLOUD_CREDS)
    cos = ibm_boto3.client("s3",
        ibm_api_key_id=c.get("IBM_COS_API_KEY"),
        ibm_service_instance_id=c.get("IBM_COS_INSTANCE_ID"),
        ibm_auth_endpoint="https://iam.cloud.ibm.com/identity/token",
        config=IBMConfig(signature_version="oauth"),
        endpoint_url=c.get("IBM_COS_ENDPOINT"))
    try:
        cos.create_bucket(Bucket=bucket_name)
    except Exception as e:
        if "BucketAlreadyExists" not in str(e) and "conflict" not in str(e).lower():
            return f"Failed to create COS bucket '{bucket_name}': {str(e)[:140]}"
    html = INDEX_HTML.replace("__AWS_STATUS_URL__", aws_status_url)
    cos.put_object(Bucket=bucket_name, Key="index.html", Body=html.encode(),
                   ContentType="text/html")
    cos.put_bucket_website(Bucket=bucket_name, WebsiteConfiguration={
        "IndexDocument": {"Suffix": "index.html"}})
    # public read for the lab (delete bucket after the event)
    cos.put_bucket_acl(Bucket=bucket_name, ACL="public-read")
    cos.put_object_acl(Bucket=bucket_name, Key="index.html", ACL="public-read")
    endpoint_host = c.get("IBM_COS_ENDPOINT").replace("https://s3.", "")
    url = f"http://{bucket_name}.s3-web.{endpoint_host}"
    return f"Done. Dashboard deployed. Open: {url}"

