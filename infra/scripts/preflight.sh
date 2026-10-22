#!/usr/bin/env bash
# Checks to run before the first deploy. Every AWS call is a read: it changes nothing.
#
#   infra/scripts/preflight.sh <aws-profile> <expected-account-id> [region]
#
# Reads used: sts GetCallerIdentity, ecs ListClusters, ec2 DescribeManagedPrefixLists,
# service-quotas GetServiceQuota, cloudformation DescribeStacks and ListStacks,
# ecr DescribeRepositories, tagging GetResources, budgets DescribeBudgets.
# Exit code 0 means no check failed. Warnings do not fail the run.
set -u

profile=${1:?usage: preflight.sh <aws-profile> <expected-account-id> [region]}
expected_account=${2:?usage: preflight.sh <aws-profile> <expected-account-id> [region]}
region=${3:-eu-west-1}
network_stack="$(cd "$(dirname "$0")" && pwd)/../seatlock_infra/network_stack.py"
min_fargate_vcpu=3

fails=0
warns=0
pass() { printf '  PASS  %s\n' "$1"; }
info() { printf '  INFO  %s\n' "$1"; }
warn() { printf '  WARN  %s\n' "$1"; warns=$((warns + 1)); }
fail() { printf '  FAIL  %s\n' "$1"; fails=$((fails + 1)); }
aws_() { aws --profile "$profile" --region "$region" --no-cli-pager "$@"; }

echo "Preflight for profile '$profile', region $region"

echo "Identity"
if ! identity=$(aws_ sts get-caller-identity --query '[Account,Arn]' --output text 2>&1); then
  fail "cannot call AWS: $identity"
  echo "  Log in first: aws sso login --profile $profile"
  exit 1
fi
account=$(echo "$identity" | cut -f1)
arn=$(echo "$identity" | cut -f2)
if [ "$account" != "$expected_account" ]; then
  fail "signed in to account $account, expected $expected_account. Stop here."
  exit 1
fi
pass "account $account"
info "as $arn"

echo "Region access"
if out=$(aws_ ecs list-clusters --query 'length(clusterArns)' --output text 2>&1); then
  pass "ECS answers in $region ($out clusters)"
else
  fail "ECS is not usable in $region. A guardrail may deny the region. $out"
fi

echo "CloudFront prefix list"
pinned=$(grep -o "\"$region\": *\"pl-[0-9a-f]*\"" "$network_stack" | grep -o 'pl-[0-9a-f]*')
actual=$(aws_ ec2 describe-managed-prefix-lists \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text 2>&1)
if [ -z "$pinned" ]; then
  fail "no prefix list is pinned for $region in network_stack.py"
elif [ "$pinned" = "$actual" ]; then
  pass "pinned $pinned matches AWS"
else
  fail "pinned '$pinned' but AWS says '$actual'. Update network_stack.py."
fi

echo "Fargate quota"
vcpu=$(aws_ service-quotas get-service-quota --service-code fargate --quota-code L-3032A538 \
  --query 'Quota.Value' --output text 2>&1)
if echo "$vcpu" | grep -Eq '^[0-9]+(\.[0-9]+)?$'; then
  if awk -v v="$vcpu" -v m="$min_fargate_vcpu" 'BEGIN { exit !(v >= m) }'; then
    pass "$vcpu on-demand vCPU allowed (need $min_fargate_vcpu)"
  else
    fail "only $vcpu on-demand vCPU allowed, need $min_fargate_vcpu. Ask for an increase."
  fi
else
  warn "could not read the quota: $vcpu"
fi

echo "CDK and existing stacks"
if status=$(aws_ cloudformation describe-stacks --stack-name CDKToolkit \
  --query 'Stacks[0].StackStatus' --output text 2>/dev/null); then
  pass "CDK is bootstrapped ($status)"
else
  info "CDK is not bootstrapped here yet. Expected on the first run."
fi
if ! stacks=$(aws_ cloudformation list-stacks \
  --query "StackSummaries[?starts_with(StackName,'Seatlock-') && StackStatus!='DELETE_COMPLETE'].[StackName,StackStatus]" \
  --output text 2>&1); then
  warn "could not list stacks: $stacks"
elif [ -z "$stacks" ]; then
  pass "no Seatlock stacks exist"
else
  warn "Seatlock stacks already exist: $(echo "$stacks" | tr '\t\n' ' ')"
fi

echo "Name clashes and leftovers"
if aws_ ecr describe-repositories --repository-names seatlock-backend > /dev/null 2>&1; then
  fail "the ECR repository seatlock-backend exists. The stack uses a fixed name and would clash."
else
  pass "no ECR repository named seatlock-backend"
fi
tagged=$(aws_ resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=seatlock \
  --query 'length(ResourceTagMappingList)' --output text 2>&1)
if [ "$tagged" = "0" ]; then
  pass "no resources tagged Project=seatlock"
elif echo "$tagged" | grep -Eq '^[0-9]+$'; then
  warn "$tagged resources are already tagged Project=seatlock"
else
  warn "could not read tagged resources: $tagged"
fi

echo "Budget"
if budgets=$(aws --profile "$profile" --region us-east-1 --no-cli-pager budgets describe-budgets \
  --account-id "$account" --query 'length(Budgets)' --output text 2>&1); then
  if [ "$budgets" = "0" ]; then
    warn "no budget exists. Create one before you deploy."
  else
    pass "$budgets budget(s) exist"
  fi
else
  warn "cannot read budgets (billing access may be off for this account): $budgets"
fi

echo "This machine"
if docker buildx inspect 2> /dev/null | grep -q 'linux/amd64'; then
  pass "docker buildx can build linux/amd64"
else
  warn "docker buildx does not list linux/amd64. The release build needs it."
fi

echo
echo "Result: $fails failed, $warns warnings"
[ "$fails" -eq 0 ]
