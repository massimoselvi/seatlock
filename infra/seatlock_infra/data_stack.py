from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_rds as rds
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from .config import Config
from .network_stack import NetworkStack

DB_NAME = "seatlock"
DB_USER = "seatlock"


class DataStack(Stack):
    """PostgreSQL, Redis and the secrets. Stateful, so it changes rarely."""

    def __init__(
        self, scope: Construct, id: str, *, config: Config, network: NetworkStack, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)
        removal = RemovalPolicy.RETAIN if config.protect_data else RemovalPolicy.DESTROY

        # Letters and digits only, so the password is safe inside a DATABASE_URL.
        self.db_secret = secretsmanager.Secret(
            self,
            "DbSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=f'{{"username": "{DB_USER}"}}',
                generate_string_key="password",
                exclude_punctuation=True,
                password_length=32,
            ),
        )
        self.django_secret = secretsmanager.Secret(
            self,
            "DjangoSecretKey",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True, password_length=64
            ),
        )

        self.database = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.of("17", "17")
            ),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO),
            vpc=network.vpc,
            vpc_subnets=network.data_subnets,
            security_groups=[network.db_sg],
            credentials=rds.Credentials.from_secret(self.db_secret),
            database_name=DB_NAME,
            allocated_storage=20,
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            multi_az=config.multi_az,
            publicly_accessible=False,
            backup_retention=Duration.days(config.db_backup_days),
            deletion_protection=config.protect_data,
            removal_policy=removal,
        )

        subnet_group = elasticache.CfnSubnetGroup(
            self,
            "CacheSubnets",
            description="Seatlock Redis",
            subnet_ids=network.vpc.select_subnets(subnet_group_name="data").subnet_ids,
        )
        self.redis = elasticache.CfnReplicationGroup(
            self,
            "Redis",
            replication_group_description="Seatlock cache, throttle counters and Celery broker",
            engine="redis",
            cache_node_type="cache.t4g.micro",
            num_cache_clusters=config.cache_nodes,
            automatic_failover_enabled=config.cache_nodes > 1,
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            cache_subnet_group_name=subnet_group.ref,
            security_group_ids=[network.cache_sg.security_group_id],
        )

    @property
    def redis_endpoint(self) -> str:
        return self.redis.attr_primary_end_point_address
