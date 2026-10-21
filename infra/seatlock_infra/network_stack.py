from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from .config import Config


class NetworkStack(Stack):
    """VPC and the three security groups. Data is reachable only from the app group."""

    def __init__(self, scope: Construct, id: str, *, config: Config, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        subnets = (
            ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ec2.SubnetConfiguration(
                name="data", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24
            ),
        )
        if not config.tasks_in_public_subnets:
            subnets += (
                ec2.SubnetConfiguration(
                    name="app", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24
                ),
            )

        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=config.nat_gateways,
            subnet_configuration=list(subnets),
        )

        self.task_subnets = (
            ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
            if config.tasks_in_public_subnets
            else ec2.SubnetSelection(subnet_group_name="app")
        )
        self.data_subnets = ec2.SubnetSelection(subnet_group_name="data")

        self.alb_sg = ec2.SecurityGroup(self, "AlbSg", vpc=self.vpc, description="Public ALB")
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP")
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")

        self.app_sg = ec2.SecurityGroup(self, "AppSg", vpc=self.vpc, description="web and worker")
        self.app_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(8000), "ALB to web")

        self.db_sg = ec2.SecurityGroup(
            self, "DbSg", vpc=self.vpc, description="PostgreSQL", allow_all_outbound=False
        )
        self.db_sg.add_ingress_rule(self.app_sg, ec2.Port.tcp(5432), "App to PostgreSQL")

        self.cache_sg = ec2.SecurityGroup(
            self, "CacheSg", vpc=self.vpc, description="Redis", allow_all_outbound=False
        )
        self.cache_sg.add_ingress_rule(self.app_sg, ec2.Port.tcp(6379), "App to Redis")

        CfnOutput(self, "AppSecurityGroupId", value=self.app_sg.security_group_id)
        CfnOutput(
            self,
            "TaskSubnetIds",
            value=",".join(self._task_subnet_ids(config)),
        )

    def _task_subnet_ids(self, config: Config) -> list[str]:
        if config.tasks_in_public_subnets:
            return self.vpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids
        return self.vpc.select_subnets(subnet_group_name="app").subnet_ids
