"""Builds an AKS cluster"""

import pulumi
from pulumi_azure_native import resources, containerservice
import pulumi_azuread as ad


config = pulumi.Config()
password = config.get_secret("password")
ssh_public_key = config.get_secret("sshPublicKey")
location = config.require("location")

resource_group = resources.ResourceGroup(
    "aksRg",
    location=location,
)

ad_app = ad.Application(
    "aksApp",
    display_name="pulumi-aks-app",
)

ad_sp = ad.ServicePrincipal("aksSp", application_id=ad_app.application_id)

ad_sp_password = ad.ServicePrincipalPassword(
    "aksSpPassword",
    service_principal_id=ad_sp.id,
    # value=password,
    end_date="2099-01-01T00:00:00Z",
)

aks_cluster_configs = [
    {
        "name": "akscluster",
        "location": location,
        "node_count": 1,
        "node_size": "standard_d2s_v5",
    },
]

cluster_names = []
for cluster_config in aks_cluster_configs:
    cluster = containerservice.ManagedCluster(
        f"aksCluster-{cluster_config['name']}",
        resource_group_name=resource_group.name,
        linux_profile=containerservice.ContainerServiceLinuxProfileArgs(
            admin_username="aksuser",
            ssh=containerservice.ContainerServiceSshConfigurationArgs(
                public_keys=[
                    containerservice.ContainerServiceSshPublicKeyArgs(
                        key_data=ssh_public_key,
                    )
                ],
            ),
        ),
        service_principal_profile=containerservice.ManagedClusterServicePrincipalProfileArgs(
            client_id=ad_app.application_id, secret=ad_sp_password.value
        ),
        location=cluster_config["location"],
        agent_pool_profiles=[
            containerservice.ManagedClusterAgentPoolProfileArgs(
                name="aksagentpool",
                mode=containerservice.AgentPoolMode.SYSTEM,
                count=cluster_config["node_count"],
                vm_size=cluster_config["node_size"],
            )
        ],
        dns_prefix=f"{pulumi.get_stack()}-kube",
        kubernetes_version="1.21.9",
    )
    cluster_names.append(cluster.name)

pulumi.export("aks_cluster_names", pulumi.Output.all(cluster_names))
pulumi.export("sp_details", pulumi.Output.all(ad_sp_password))
