import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from seatlock_infra.config import DEMO, PROD
from seatlock_infra.network_stack import CLOUDFRONT_ORIGIN_PREFIX_LISTS
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


def test_load_balancer_accepts_traffic_only_from_cloudfront(demo):
    network = demo["network"]
    from_cloudfront = network.find_resources(
        "AWS::EC2::SecurityGroupIngress", {"Properties": {"Description": "CloudFront to ALB"}}
    )
    ((_, rule),) = from_cloudfront.items()
    assert rule["Properties"]["SourcePrefixListId"] == CLOUDFRONT_ORIGIN_PREFIX_LISTS["eu-west-1"]
    assert (rule["Properties"]["FromPort"], rule["Properties"]["ToPort"]) == (80, 80)

    # The group itself holds no inline rule, and no ingress rule in the stack is open to the world.
    group = network.find_resources(
        "AWS::EC2::SecurityGroup",
        {"Properties": {"GroupDescription": Match.string_like_regexp("^ALB")}},
    )
    ((_, alb),) = group.items()
    assert "SecurityGroupIngress" not in alb["Properties"]
    every_rule = network.find_resources("AWS::EC2::SecurityGroupIngress")
    assert not any({"CidrIp", "CidrIpv6"} & set(r["Properties"]) for r in every_rule.values())


def test_resources_are_tagged_for_cost_and_cleanup(demo):
    # CloudFormation lists tags in alphabetical order.
    demo["network"].has_resource_properties(
        "AWS::EC2::VPC",
        {
            "Tags": Match.array_with(
                [
                    {"Key": "Env", "Value": "demo"},
                    {"Key": "ManagedBy", "Value": "cdk"},
                    {"Key": "Project", "Value": "seatlock"},
                ]
            )
        },
    )


def test_destroy_by_tag_is_added_when_given():
    stacks = build(cdk.App(context={"destroy_by": "2026-10-23"}), DEMO)
    Template.from_stack(stacks.network).has_resource_properties(
        "AWS::EC2::VPC", {"Tags": Match.array_with([{"Key": "DestroyBy", "Value": "2026-10-23"}])}
    )


def test_outputs_needed_by_the_deploy_guide_exist(demo):
    needed = {
        "network": {"AppSecurityGroupId", "TaskSubnetIds"},
        "app": {
            "RepositoryUri",
            "ClusterName",
            "WebServiceName",
            "WorkerServiceName",
            "WebTaskFamily",
        },
        "frontend": {"BucketName", "DistributionId", "SiteUrl"},
    }
    for stack, names in needed.items():
        assert names <= set(demo[stack].to_json()["Outputs"])


def test_bootstrap_starts_no_tasks_until_an_image_exists():
    from dataclasses import replace

    template = synth(replace(DEMO, bootstrap=True))["app"]
    services = template.find_resources("AWS::ECS::Service")
    assert {s["Properties"]["DesiredCount"] for s in services.values()} == {0}


def test_admin_paths_are_blocked_at_the_load_balancer(demo):
    demo["app"].has_resource_properties(
        "AWS::ElasticLoadBalancingV2::ListenerRule",
        {
            "Priority": 1,
            "Conditions": [
                {"Field": "path-pattern", "PathPatternConfig": {"Values": ["/admin", "/admin/*"]}}
            ],
            "Actions": [
                Match.object_like(
                    {
                        "Type": "fixed-response",
                        "FixedResponseConfig": Match.object_like({"StatusCode": "403"}),
                    }
                )
            ],
        },
    )
