from aws_cdk import RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import Config


class FrontendStack(Stack):
    """Private S3 bucket for the Vue build, served by CloudFront. /api/* goes to the ALB."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: Config,
        alb: elbv2.IApplicationLoadBalancer,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.bucket = s3.Bucket(
            self,
            "Site",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN if config.protect_data else RemovalPolicy.DESTROY,
            auto_delete_objects=not config.protect_data,
        )

        api_origin = origins.LoadBalancerV2Origin(
            alb, protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY
        )
        self.distribution = cloudfront.Distribution(
            self,
            "Cdn",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                )
            },
            # Single-page app: unknown paths fall back to index.html.
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=status, response_http_status=200, response_page_path="/index.html"
                )
                for status in (403, 404)
            ],
        )
