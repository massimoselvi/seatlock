"""CloudFront pieces shared by the frontend and app stacks (ADR 0007)."""

from aws_cdk import Duration
from aws_cdk import aws_cloudfront as cloudfront
from constructs import Construct

ORIGIN_VERIFY_HEADER = "X-Origin-Verify"

# The theme script is a separate file, so scripts need no 'unsafe-inline'. Vue sets inline styles
# through the style API, which style-src 'self' allows.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)

# A path with no dot is a screen of the single-page app. Only the site behavior runs this, so
# the API keeps its real 403 and 404 answers (a distribution-wide error page would hide them).
SPA_REWRITE = """\
function handler(event) {
  var request = event.request;
  if (request.uri.indexOf('.') === -1) request.uri = '/index.html';
  return request;
}
"""


def spa_rewrite_function(scope: Construct) -> cloudfront.Function:
    return cloudfront.Function(
        scope,
        "SpaRewrite",
        code=cloudfront.FunctionCode.from_inline(SPA_REWRITE),
        runtime=cloudfront.FunctionRuntime.JS_2_0,
    )


def security_headers_policy(scope: Construct) -> cloudfront.ResponseHeadersPolicy:
    return cloudfront.ResponseHeadersPolicy(
        scope,
        "SecurityHeaders",
        security_headers_behavior=cloudfront.ResponseSecurityHeadersBehavior(
            content_security_policy=cloudfront.ResponseHeadersContentSecurityPolicy(
                content_security_policy=CONTENT_SECURITY_POLICY, override=True
            ),
            strict_transport_security=cloudfront.ResponseHeadersStrictTransportSecurity(
                access_control_max_age=Duration.days(365), include_subdomains=True, override=True
            ),
            content_type_options=cloudfront.ResponseHeadersContentTypeOptions(override=True),
            frame_options=cloudfront.ResponseHeadersFrameOptions(
                frame_option=cloudfront.HeadersFrameOption.DENY, override=True
            ),
            referrer_policy=cloudfront.ResponseHeadersReferrerPolicy(
                referrer_policy=cloudfront.HeadersReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN,
                override=True,
            ),
        ),
    )
