#!/usr/bin/env bash
# Prints the facts for a weekly status report from GitHub. It only reads.
#
#   docs/pm/tools/weekly-data.sh <from-date> <to-date>
#   docs/pm/tools/weekly-data.sh 2026-10-20 2026-10-23
#
# Dates are YYYY-MM-DD and inclusive. Needs the GitHub CLI, signed in.
set -euo pipefail

from=${1:?usage: weekly-data.sh <from-date> <to-date>}
to=${2:?usage: weekly-data.sh <from-date> <to-date>}
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

echo "## Facts for $from to $to ($repo)"
echo

echo "### Merged pull requests"
gh pr list --state merged --search "merged:$from..$to" --limit 200 \
  --json number,title,mergedAt,additions,deletions \
  --jq 'sort_by(.number) | .[] | "- #\(.number) \(.title) (\(.mergedAt[0:10]), +\(.additions)/-\(.deletions))"'
count=$(gh pr list --state merged --search "merged:$from..$to" --limit 200 --json number --jq length)
echo "Total: $count"
echo

echo "### Closed issues"
gh issue list --state closed --search "closed:$from..$to" --limit 200 \
  --json number,title,milestone \
  --jq 'sort_by(.number) | .[] | "- #\(.number) \(.title) [\(.milestone.title // "no milestone")]"'
echo "Total: $(gh issue list --state closed --search "closed:$from..$to" --limit 200 --json number --jq length)"
echo

echo "### Opened issues"
gh issue list --state all --search "created:$from..$to" --limit 200 \
  --json number,title,state \
  --jq 'sort_by(.number) | .[] | "- #\(.number) \(.title) (\(.state))"'
echo

echo "### Open work now, by milestone"
gh issue list --state open --limit 200 --json number,milestone \
  --jq 'group_by(.milestone.title // "no milestone") | .[] | "- \(.[0].milestone.title // "no milestone"): \(length) open"'
echo
echo "### Blocked issues"
gh issue list --state open --label blocked --limit 50 --json number,title \
  --jq '.[] | "- #\(.number) \(.title)"'
echo

echo "### Milestones"
gh api "repos/$repo/milestones?state=all&per_page=50" \
  --jq 'sort_by(.title) | .[] | "- \(.title) [\(.state)]: \(.open_issues) open, \(.closed_issues) closed, due \(.due_on // "none" | .[0:10])"'
echo

echo "### Commits on main"
git log origin/main --since="$from 00:00" --until="$to 23:59:59" --format=%as | sort | uniq -c \
  | awk '{printf "- %s: %s commits\n", $2, $1}'
echo "Total: $(git log origin/main --since="$from 00:00" --until="$to 23:59:59" --oneline | wc -l | tr -d ' ')"
echo

echo "### Last runs on main"
gh run list --branch main --limit 5 --json workflowName,conclusion,createdAt \
  --jq '.[] | "- \(.workflowName): \(.conclusion) (\(.createdAt[0:16]))"'
