"""Environment settings. Demo and production differ by values, not by code (ADR 0004)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    name: str
    multi_az: bool
    nat_gateways: int
    web_count: int
    cache_nodes: int
    db_backup_days: int
    protect_data: bool
    alarm_email: str | None = None
    image_tag: str = "latest"

    @property
    def tasks_in_public_subnets(self) -> bool:
        """Without a NAT gateway, tasks need public IPs to reach ECR and AWS APIs."""
        return self.nat_gateways == 0


DEMO = Config(
    name="demo",
    multi_az=False,
    nat_gateways=0,
    web_count=2,
    cache_nodes=1,
    db_backup_days=1,
    protect_data=False,
)

PROD = Config(
    name="prod",
    multi_az=True,
    nat_gateways=1,
    web_count=2,
    cache_nodes=2,
    db_backup_days=7,
    protect_data=True,
)

ENVIRONMENTS = {"demo": DEMO, "prod": PROD}
