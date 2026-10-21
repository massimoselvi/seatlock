from dataclasses import dataclass

import aws_cdk as cdk

from .app_stack import AppStack
from .config import Config
from .data_stack import DataStack
from .frontend_stack import FrontendStack
from .network_stack import NetworkStack

# Region comes from here. Nothing needs an AWS account to synth.
ENV = cdk.Environment(region="eu-west-1")


@dataclass(frozen=True)
class Stacks:
    network: NetworkStack
    data: DataStack
    app: AppStack
    frontend: FrontendStack


def build(app: cdk.App, config: Config) -> Stacks:
    prefix = f"Seatlock-{config.name}"
    network = NetworkStack(app, f"{prefix}-Network", config=config, env=ENV)
    data = DataStack(app, f"{prefix}-Data", config=config, network=network, env=ENV)
    application = AppStack(app, f"{prefix}-App", config=config, network=network, data=data, env=ENV)
    frontend = FrontendStack(app, f"{prefix}-Frontend", config=config, alb=application.alb, env=ENV)
    return Stacks(network, data, application, frontend)
