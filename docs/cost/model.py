#!/usr/bin/env python3
"""Monthly cost model for the architecture in ADR 0003. Standard library only.

Run: python3 docs/cost/model.py
Prices are USD, eu-west-1 (Ireland), on demand, from the AWS Price List Bulk API
(publication 2026-10-20). Change a price or a scenario below and rerun.
"""

H = 730  # hours in a month, the figure AWS uses for monthly estimates

# --- Unit prices -----------------------------------------------------------------------------
P = {
    "fargate_vcpu_x86": 0.04048,  # per vCPU-hour
    "fargate_gb_x86": 0.004445,  # per GB-hour
    "fargate_vcpu_arm": 0.03238,
    "fargate_gb_arm": 0.00356,
    "rds_micro_single": 0.017,  # db.t4g.micro PostgreSQL, per hour
    "rds_micro_multi": 0.035,
    "rds_gp3_single": 0.127,  # per GB-month
    "rds_gp3_multi": 0.254,
    "redis_micro": 0.017,  # cache.t4g.micro, per node-hour
    "alb_hour": 0.0252,
    "alb_lcu_hour": 0.008,
    "ipv4_hour": 0.005,  # every public IPv4 address, in use
    "nat_hour": 0.048,
    "nat_gb": 0.048,
    "cw_logs_ingest_gb": 0.57,
    "cw_logs_store_gb": 0.03,
    "cw_alarm_metric": 0.10,  # standard resolution, per metric in the alarm
    "cw_custom_metric": 0.30,
    "secret": 0.40,  # per secret-month
    "ecr_gb": 0.10,
    "s3_gb": 0.023,
    "cf_https_per_10k": 0.012,  # Europe, after the free tier
    "cf_gb": 0.085,  # Europe, first 10 TB, after the free tier
    "cf_free_requests": 10_000_000,  # always-free tier, per month
    "cf_free_gb": 1024,
    "waf_acl": 5.00,
    "waf_rule": 1.00,
    "waf_per_million": 0.60,
    "route53_zone": 0.50,
    "ses_per_email": 0.0001,
    "vpc_endpoint_hour": 0.011,  # interface endpoint, per AZ
}


def fargate(vcpu, gb, count, arm=False):
    suffix = "arm" if arm else "x86"
    return count * H * (vcpu * P[f"fargate_vcpu_{suffix}"] + gb * P[f"fargate_gb_{suffix}"])


# --- Scenarios -------------------------------------------------------------------------------
# traffic: requests per month, response GB per month, log GB, emails, ALB LCU average, NAT GB
TRAFFIC = {
    "low": dict(requests=50_000, out_gb=1, log_gb=0.5, emails=100, lcu=0.1, nat_gb=1),
    "expected": dict(requests=2_000_000, out_gb=10, log_gb=2, emails=2_000, lcu=0.5, nat_gb=4),
    "high": dict(requests=40_000_000, out_gb=400, log_gb=20, emails=40_000, lcu=2.0, nat_gb=25),
}

SETUPS = {
    # Disposable. One AZ, no NAT: tasks sit in public subnets and each holds a public IPv4.
    "demo": dict(web=2, worker=1, multi_az=False, redis_nodes=1, nat=0, arm=False),
    "demo-lean": dict(web=1, worker=1, multi_az=False, redis_nodes=1, nat=0, arm=True),
    "prod": dict(web=2, worker=1, multi_az=True, redis_nodes=2, nat=1, arm=False),
    "prod-arm": dict(web=2, worker=1, multi_az=True, redis_nodes=2, nat=1, arm=True),
}


def cost(setup, traffic, waf=False, logging=True):
    s, t = SETUPS[setup], TRAFFIC[traffic]
    tasks = s["web"] + s["worker"]
    lines = {}
    lines["Fargate (web + worker)"] = fargate(0.5, 1, s["web"], s["arm"]) + fargate(
        0.25, 0.5, s["worker"], s["arm"]
    )
    lines["RDS PostgreSQL instance"] = H * P["rds_micro_multi" if s["multi_az"] else "rds_micro_single"]
    lines["RDS storage, 20 GB gp3"] = 20 * P["rds_gp3_multi" if s["multi_az"] else "rds_gp3_single"]
    lines["ElastiCache Redis"] = s["redis_nodes"] * H * P["redis_micro"]
    lines["ALB hours + LCU"] = H * P["alb_hour"] + t["lcu"] * H * P["alb_lcu_hour"]
    ipv4 = 2  # ALB: one address per AZ
    ipv4 += tasks if s["nat"] == 0 else s["nat"]  # public tasks, or the NAT gateway address
    lines["Public IPv4 addresses"] = ipv4 * H * P["ipv4_hour"]
    lines["NAT gateway (hours + data)"] = s["nat"] * (H * P["nat_hour"] + t["nat_gb"] * P["nat_gb"])
    lines["CloudWatch logs"] = t["log_gb"] * (P["cw_logs_ingest_gb"] + P["cw_logs_store_gb"])
    lines["CloudWatch alarms (6) + 2 custom metrics"] = 7 * P["cw_alarm_metric"] + 2 * P["cw_custom_metric"]
    lines["Secrets Manager (2 secrets)"] = 2 * P["secret"]
    lines["ECR, S3 site, Route 53 zone"] = 1 * P["ecr_gb"] + 0.1 * P["s3_gb"] + P["route53_zone"]
    billable_req = max(t["requests"] - P["cf_free_requests"], 0)
    billable_gb = max(t["out_gb"] - P["cf_free_gb"], 0)
    lines["CloudFront (after free tier)"] = (
        billable_req / 10_000 * P["cf_https_per_10k"] + billable_gb * P["cf_gb"]
    )
    lines["SES email"] = t["emails"] * P["ses_per_email"]
    if logging:
        lines["Access logs in S3 (ALB, CloudFront)"] = 0.3 * (1 + t["out_gb"] / 100)
    if waf:
        lines["WAF (1 ACL, 4 rules, requests)"] = (
            P["waf_acl"] + 4 * P["waf_rule"] + t["requests"] / 1_000_000 * P["waf_per_million"]
        )
    return lines


def total(lines):
    return sum(lines.values())


if __name__ == "__main__":
    print(f"{'setup':<11}{'traffic':<10}{'USD/month':>10}{'  with WAF':>11}")
    for setup in SETUPS:
        for traffic in TRAFFIC:
            base = total(cost(setup, traffic))
            waf = total(cost(setup, traffic, waf=True))
            print(f"{setup:<11}{traffic:<10}{base:>10.2f}{waf:>11.2f}")
    print()
    for setup, traffic in (("demo", "low"), ("prod", "expected")):
        print(f"Breakdown: {setup}, {traffic} traffic")
        for name, usd in cost(setup, traffic).items():
            print(f"  {name:<44}{usd:>8.2f}")
        print(f"  {'Total':<44}{total(cost(setup, traffic)):>8.2f}")
        print()
    # Questions the ADR asks
    print("NAT gateway vs VPC interface endpoints (2 AZ, 4 endpoints: ECR api, ECR dkr, Secrets, Logs)")
    nat = H * P["nat_hour"] + P["ipv4_hour"] * H
    endpoints = 4 * 2 * H * P["vpc_endpoint_hour"]
    print(f"  NAT + its address: {nat:.2f}   endpoints: {endpoints:.2f}")
    print()
    idle = total(cost("demo", "low"))
    fixed = idle - fargate(0.5, 1, 2) - fargate(0.25, 0.5, 1) - 3 * H * P["ipv4_hour"]
    print(f"Demo idle floor with tasks scaled to zero: {fixed:.2f}  (running: {idle:.2f}, {idle / H:.3f}/hour)")
