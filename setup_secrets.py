import getpass

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import workspace

w = WorkspaceClient()

w.secrets.create_scope(scope="database")

w.secrets.put_secret(
    scope="database",
    key="lakebase-url",
    string_value=getpass.getpass("Paste your Lakebase URL: ")
)

w.secrets.put_acl(
    scope="database",
    principal="users",
    permission=workspace.AclPermission.READ,
)