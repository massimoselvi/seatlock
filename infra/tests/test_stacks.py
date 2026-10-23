import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from seatlock_infra.config import DEMO, PROD
from seatlock_infra.network_stack import CLOUDFRONT_ORIGIN_PREFIX_LISTS
from seatlock_infra.stacks import build


def synth(config):
    stacks = build(cdk.App(context={"image_tag": "test"}), config)
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
        assert {"SECRET_KEY", "DB_PASSWORD", "REDIS_PASSWORD"} <= secret_names
        assert not {"SECRET_KEY", "DB_PASSWORD", "REDIS_PASSWORD"} & env_names


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
    stacks = build(cdk.App(context={"destroy_by": "2026-10-23", "image_tag": "test"}), DEMO)
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


def test_api_errors_are_not_replaced_by_the_single_page_app(demo):
    """A distribution-wide error page turned API 403 and 404 into 200 with HTML."""
    config = demo["frontend"].find_resources("AWS::CloudFront::Distribution")
    ((_, cdn),) = config.items()
    assert "CustomErrorResponses" not in cdn["Properties"]["DistributionConfig"]
    demo["frontend"].has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "DefaultCacheBehavior": Match.object_like(
                        {
                            "FunctionAssociations": [
                                Match.object_like({"EventType": "viewer-request"})
                            ]
                        }
                    )
                }
            )
        },
    )


def test_security_headers_are_sent_on_site_and_api(demo):
    demo["frontend"].has_resource_properties(
        "AWS::CloudFront::ResponseHeadersPolicy",
        {
            "ResponseHeadersPolicyConfig": Match.object_like(
                {
                    "SecurityHeadersConfig": Match.object_like(
                        {
                            "ContentSecurityPolicy": Match.object_like(
                                {
                                    "ContentSecurityPolicy": Match.string_like_regexp(
                                        "script-src 'self'"
                                    )
                                }
                            ),
                            "StrictTransportSecurity": Match.object_like({"Override": True}),
                            "ContentTypeOptions": {"Override": True},
                            "FrameOptions": Match.object_like({"FrameOption": "DENY"}),
                        }
                    )
                }
            )
        },
    )


def test_load_balancer_serves_only_requests_with_the_cloudfront_secret(demo):
    demo["app"].has_resource_properties(
        "AWS::ElasticLoadBalancingV2::Listener",
        {
            "DefaultActions": [
                Match.object_like(
                    {
                        "Type": "fixed-response",
                        "FixedResponseConfig": Match.object_like({"StatusCode": "403"}),
                    }
                )
            ]
        },
    )
    demo["app"].has_resource_properties(
        "AWS::ElasticLoadBalancingV2::ListenerRule",
        {
            "Conditions": [
                Match.object_like(
                    {
                        "Field": "http-header",
                        "HttpHeaderConfig": Match.object_like(
                            {"HttpHeaderName": "X-Origin-Verify"}
                        ),
                    }
                )
            ],
            "Actions": [Match.object_like({"Type": "forward"})],
        },
    )
    demo["frontend"].has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "Origins": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "OriginCustomHeaders": [
                                        Match.object_like({"HeaderName": "X-Origin-Verify"})
                                    ]
                                }
                            )
                        ]
                    )
                }
            )
        },
    )


def test_image_tags_are_immutable_and_a_tag_is_required():
    from dataclasses import replace

    synth(DEMO)["app"].has_resource_properties(
        "AWS::ECR::Repository", {"ImageTagMutability": "IMMUTABLE"}
    )
    with pytest.raises(ValueError, match="image_tag"):
        build(cdk.App(), DEMO)
    build(cdk.App(), replace(DEMO, bootstrap=True))  # bootstrap runs no task, so needs no tag


def test_redis_requires_an_auth_token(demo):
    demo["data"].has_resource_properties(
        "AWS::ElastiCache::ReplicationGroup", {"AuthToken": Match.any_value()}
    )


def test_prod_has_waf_and_access_logs_and_demo_does_not(demo, prod):
    prod["app"].resource_count_is("AWS::WAFv2::WebACL", 1)
    prod["app"].resource_count_is("AWS::WAFv2::WebACLAssociation", 1)
    prod["app"].has_resource_properties(
        "AWS::ElasticLoadBalancingV2::LoadBalancer",
        {
            "LoadBalancerAttributes": Match.array_with(
                [{"Key": "access_logs.s3.enabled", "Value": "true"}]
            )
        },
    )
    demo["app"].resource_count_is("AWS::WAFv2::WebACL", 0)
