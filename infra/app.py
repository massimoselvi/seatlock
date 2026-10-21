#!/usr/bin/env python3
from dataclasses import replace

import aws_cdk as cdk

from seatlock_infra.config import ENVIRONMENTS
from seatlock_infra.stacks import build

app = cdk.App()
config = ENVIRONMENTS[app.node.try_get_context("env") or "demo"]
if email := app.node.try_get_context("alarm_email"):
    config = replace(config, alarm_email=email)

if app.node.try_get_context("bootstrap"):
    config = replace(config, bootstrap=True)

build(app, config)
app.synth()
