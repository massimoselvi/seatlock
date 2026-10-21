import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from seatlock_infra.config import DEMO, PROD
from seatlock_infra.stacks import build


def synth(config):
    stacks = build(cdk.App(), config)
    return {
        "network": Template.from_stack(stacks.network),
        "data": Template.from_stack(stacks.data),
        "app": Template.from_stack(stacks.app),
        "frontend": Template.from_stack(stacks.frontend),
    }


@pytest.fixture(scope="module")
def demo():
    return synth(DEMO)


@pytest.fixture(scope="module")
def prod():
    return synth(PROD)


def test_database_is_private_and_encrypted(demo):
    demo["data"].has_resource_properties(
        "AWS::RDS::DBInstance",
        {"PubliclyAccessible": False, "StorageEncrypted": True, "Engine": "postgres"},
    )


def test_database_accepts_traffic_only_from_the_app_group(demo):
    rules = demo["network"].find_resources("AWS::EC2::SecurityGroupIngress")
    to_postgres = [r for r in rules.values() if r["Properties"].get("FromPort") == 5432]
    assert len(to_postgres) == 1
    assert "SourceSecurityGroupId" in to_postgres[0]["Properties"]
    assert "CidrIp" not in to_postgres[0]["Properties"]


def test_redis_is_encrypted_in_transit_and_at_rest(demo):
    demo["data"].has_resource_properties(
        "AWS::ElastiCache::ReplicationGroup",
        {"TransitEncryptionEnabled": True, "AtRestEncryptionEnabled": True},
    )


def test_prod_is_highly_available_and_protected(prod):
    prod["data"].has_resource_properties(
        "AWS::RDS::DBInstance", {"MultiAZ": True, "DeletionProtection": True}
    )
    prod["data"].has_resource_properties(
        "AWS::ElastiCache::ReplicationGroup",
        {"NumCacheClusters": 2, "AutomaticFailoverEnabled": True},
    )
    prod["data"].has_resource("AWS::RDS::DBInstance", {"DeletionPolicy": "Retain"})
    prod["network"].resource_count_is("AWS::EC2::NatGateway", 1)


def test_demo_is_cheap_and_disposable(demo):
    demo["data"].has_resource_properties(
        "AWS::RDS::DBInstance", {"MultiAZ": False, "DeletionProtection": False}
    )
    demo["network"].resource_count_is("AWS::EC2::NatGateway", 0)


def test_web_and_worker_services_run_on_fargate(demo):
    demo["app"].resource_count_is("AWS::ECS::Service", 2)
    demo["app"].has_resource_properties(
        "AWS::ECS::Service",
        {
            "LaunchType": "FARGATE",
            "DesiredCount": DEMO.web_count,
            "DeploymentConfiguration": Match.object_like(
                {"DeploymentCircuitBreaker": {"Enable": True, "Rollback": True}}
            ),
        },
    )


def test_tasks_get_secrets_from_secrets_manager_not_plain_environment(demo):
    definitions = demo["app"].find_resources("AWS::ECS::TaskDefinition")
    for definition in definitions.values():
        container = definition["Properties"]["ContainerDefinitions"][0]
        secret_names = {s["Name"] for s in container["Secrets"]}
        env_names = {e["Name"] for e in container["Environment"]}
        assert {"SECRET_KEY", "DB_PASSWORD"} <= secret_names
        assert not {"SECRET_KEY", "DB_PASSWORD"} & env_names


def test_load_balancer_checks_the_health_endpoint(demo):
    demo["app"].has_resource_properties(
        "AWS::ElasticLoadBalancingV2::TargetGroup", {"HealthCheckPath": "/api/health/"}
    )


def test_alarms_from_the_slo_document_exist(demo):
    alarms = demo["app"].find_resources("AWS::CloudWatch::Alarm")
    assert len(alarms) == 4


def test_site_bucket_is_private_and_api_is_routed_to_the_load_balancer(demo):
    demo["frontend"].has_resource_properties(
        "AWS::S3::Bucket",
        {"PublicAccessBlockConfiguration": Match.object_like({"BlockPublicAcls": True})},
    )
    demo["frontend"].has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {"CacheBehaviors": [Match.object_like({"PathPattern": "/api/*"})]}
            )
        },
    )
