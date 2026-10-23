from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct

from .config import Config
from .data_stack import DB_NAME, DB_USER, DataStack
from .edge import ORIGIN_VERIFY_HEADER
from .network_stack import NetworkStack

# Migrations are not run here. Several tasks starting together must not race on them.
# They run once per release as a one-off task (see docs/deploy.md).
# --no-control-socket: the app user has no home directory, so the default socket under $HOME
# fails to open and every start logs an error.
WEB_COMMAND = (
    "exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 --access-logfile - "
    "--no-control-socket"
)
WORKER_COMMAND = "exec celery -A config worker --loglevel=info"


class AppStack(Stack):
    """ECR, the ECS cluster, web and worker services, the ALB and the alarms from docs/slo.md."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: Config,
        network: NetworkStack,
        data: DataStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.config = config
        removal = RemovalPolicy.RETAIN if config.protect_data else RemovalPolicy.DESTROY

        self.repository = ecr.Repository(
            self,
            "Backend",
            repository_name="seatlock-backend",
            image_scan_on_push=True,
            # A tag is a release. It never moves, so a rollback runs the code that was tested.
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            removal_policy=removal,
            empty_on_delete=not config.protect_data,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=20)],
        )
        cluster = ecs.Cluster(self, "Cluster", vpc=network.vpc)

        redis_host = data.redis_endpoint
        environment = {
            "DEBUG": "false",
            # The ALB health check calls the task by IP, so Django cannot filter hosts. The ALB
            # forwards only requests that carry the CloudFront secret header, which replaces it.
            "ALLOWED_HOSTS": "*",
            "ADMIN_ENABLED": "false",
            # Flip to "true" with the HTTPS listener from issue #47. Until then the ALB hop is HTTP.
            "FORCE_HTTPS": "false",
            # Client IP is the second address from the right: viewer, then the CloudFront edge.
            "NUM_PROXIES": "2",
            "DB_HOST": data.database.db_instance_endpoint_address,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "REDIS_HOST": redis_host,
        }
        secrets = {
            "SECRET_KEY": ecs.Secret.from_secrets_manager(data.django_secret),
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(data.db_secret, "password"),
            "REDIS_PASSWORD": ecs.Secret.from_secrets_manager(data.redis_secret),
        }

        web = self._task(
            "Web",
            cpu=512,
            memory=1024,
            command=WEB_COMMAND,
            env=environment,
            secrets=secrets,
            port=8000,
        )
        worker = self._task(
            "Worker", cpu=256, memory=512, command=WORKER_COMMAND, env=environment, secrets=secrets
        )

        self.web_service = self._service(
            "WebService", cluster, web, network, config, desired=config.web_desired
        )
        worker_service = self._service(
            "WorkerService", cluster, worker, network, config, desired=config.worker_desired
        )

        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=network.vpc,
            internet_facing=True,
            security_group=network.alb_sg,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            deletion_protection=config.protect_data,
        )
        # Anything without the CloudFront secret header gets a 403, including other CloudFront
        # distributions, which share the address list the security group allows.
        listener = self.alb.add_listener(
            "Http",
            port=80,
            open=False,
            default_action=elbv2.ListenerAction.fixed_response(
                403, content_type="text/plain", message_body="Forbidden"
            ),
        )
        target_group = listener.add_targets(
            "Web",
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[self.web_service],
            priority=10,
            conditions=[
                elbv2.ListenerCondition.http_header(
                    ORIGIN_VERIFY_HEADER, [data.origin_secret.secret_value.unsafe_unwrap()]
                )
            ],
            health_check=elbv2.HealthCheck(path="/api/health/", healthy_http_codes="200"),
            deregistration_delay=Duration.seconds(30),
        )

        # The ALB is public. Keep the Django admin off it, whatever the app is configured to do.
        listener.add_action(
            "BlockAdmin",
            priority=1,
            conditions=[elbv2.ListenerCondition.path_patterns(["/admin", "/admin/*"])],
            action=elbv2.ListenerAction.fixed_response(
                403, content_type="text/plain", message_body="Forbidden"
            ),
        )

        self._alarms(config, data, target_group)
        if config.alb_logs:
            self._access_logs(removal)
        if config.waf:
            self._waf()

        # Used by docs/deploy.md so the release steps need no console lookups.
        CfnOutput(self, "RepositoryUri", value=self.repository.repository_uri)
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)
        CfnOutput(self, "WebServiceName", value=self.web_service.service_name)
        CfnOutput(self, "WorkerServiceName", value=worker_service.service_name)
        CfnOutput(self, "WebTaskFamily", value=web.family)

    def _access_logs(self, removal):
        bucket = s3.Bucket(
            self,
            "AlbLogs",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=removal,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(90))],
        )
        self.alb.log_access_logs(bucket)

    def _waf(self):
        """AWS managed rule groups on the ALB. Rate limits stay in the app (see ADR 0007)."""

        def group(priority, name):
            return wafv2.CfnWebACL.RuleProperty(
                name=name,
                priority=priority,
                override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                statement=wafv2.CfnWebACL.StatementProperty(
                    managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                        vendor_name="AWS", name=name
                    )
                ),
                visibility_config=self._waf_visibility(name),
            )

        acl = wafv2.CfnWebACL(
            self,
            "WebAcl",
            scope="REGIONAL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=self._waf_visibility("seatlock"),
            rules=[
                group(1, "AWSManagedRulesAmazonIpReputationList"),
                group(2, "AWSManagedRulesKnownBadInputsRuleSet"),
                group(3, "AWSManagedRulesCommonRuleSet"),
            ],
        )
        wafv2.CfnWebACLAssociation(
            self,
            "WebAclAssociation",
            resource_arn=self.alb.load_balancer_arn,
            web_acl_arn=acl.attr_arn,
        )

    @staticmethod
    def _waf_visibility(name):
        return wafv2.CfnWebACL.VisibilityConfigProperty(
            cloud_watch_metrics_enabled=True, metric_name=name, sampled_requests_enabled=True
        )

    def _task(self, name, *, cpu, memory, command, env, secrets, port=None):
        task = ecs.FargateTaskDefinition(self, f"{name}Task", cpu=cpu, memory_limit_mib=memory)
        # DATABASE_URL is built at start-up so the password never sits in the task definition.
        script = (
            "export DATABASE_URL=postgres://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME"
            "?sslmode=require && "
            "export CELERY_BROKER_URL=rediss://:$REDIS_PASSWORD@$REDIS_HOST:6379/0"
            "?ssl_cert_reqs=required && "
            "export CACHE_URL=rediss://:$REDIS_PASSWORD@$REDIS_HOST:6379/1 && " + command
        )
        container = task.add_container(
            name.lower(),
            image=ecs.ContainerImage.from_ecr_repository(self.repository, tag=self._tag),
            command=["sh", "-c", script],
            environment=env,
            secrets=secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix=name.lower(), log_retention=logs.RetentionDays.ONE_MONTH
            ),
        )
        if port:
            container.add_port_mappings(ecs.PortMapping(container_port=port))
        return task

    @property
    def _tag(self) -> str:
        tag = self.node.try_get_context("image_tag")
        if tag:
            return tag
        if self.config.bootstrap:
            return "bootstrap"  # no tasks run yet, so no image is pulled
        raise ValueError(
            "Pass -c image_tag=<git sha>. Tags are immutable and there is no 'latest'."
        )

    def _service(self, name, cluster, task, network, config, *, desired):
        return ecs.FargateService(
            self,
            name,
            cluster=cluster,
            task_definition=task,
            desired_count=desired,
            security_groups=[network.app_sg],
            vpc_subnets=network.task_subnets,
            assign_public_ip=config.tasks_in_public_subnets,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

    def _alarms(self, config, data, target_group):
        topic = sns.Topic(self, "Alarms")
        if config.alarm_email:
            topic.add_subscription(subscriptions.EmailSubscription(config.alarm_email))
        action = cw_actions.SnsAction(topic)

        errors = cloudwatch.MathExpression(
            expression="IF(requests > 0, 100 * errors / requests, 0)",
            using_metrics={
                "errors": self.alb.metrics.http_code_target(
                    elbv2.HttpCodeTarget.TARGET_5XX_COUNT, statistic="Sum"
                ),
                "requests": self.alb.metrics.request_count(statistic="Sum"),
            },
            period=Duration.minutes(5),
        )
        self._alarm("HighErrorRate", errors, 2, "5xx above 2% for 5 minutes", action)

        latency = target_group.metrics.target_response_time(
            statistic="p95", period=Duration.minutes(5)
        )
        self._alarm(
            "SlowRequests", latency, 0.8, "p95 above 800 ms for 10 minutes", action, periods=2
        )

        db_cpu = data.database.metric_cpu_utilization(period=Duration.minutes(5))
        self._alarm(
            "DatabaseCpu", db_cpu, 80, "Database CPU above 80% for 10 minutes", action, periods=2
        )

        unhealthy = target_group.metrics.unhealthy_host_count(period=Duration.minutes(1))
        self._alarm(
            "UnhealthyWebTasks",
            unhealthy,
            1,
            "A web task is unhealthy",
            action,
            periods=3,
            operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

    def _alarm(self, id, metric, threshold, description, action, *, periods=1, operator=None):
        alarm = cloudwatch.Alarm(
            self,
            id,
            metric=metric,
            threshold=threshold,
            evaluation_periods=periods,
            comparison_operator=operator or cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description=description,
        )
        alarm.add_alarm_action(action)
