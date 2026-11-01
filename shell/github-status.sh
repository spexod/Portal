#!/bin/bash
# Save the GitHub state of both repositories into logs/github/ (gitignored), for reading in the sandbox:
# workflow runs with their jobs, the logs of failed jobs, open and recently closed pull requests
# (Dependabot's among them), and Dependabot security alerts.
#
#   ./shell/github-status.sh            # last 15 runs per repository
#   ./shell/github-status.sh 40         # more history
#
# Needs the gh CLI logged in (on the development computer: gh auth login; in the sandbox, the GitHub
# secret set with sbx on the host, see CLAUDE.md "Git Authentication"). Read-only: nothing is changed.
set -uo pipefail
cd "$(dirname "$0")/.."
limit=${1:-15}
out=logs/github
mkdir -p "$out"
stamp=$(date -u +%Y-%m-%dT%H:%MZ)
{
echo "GitHub status $stamp (runs: $limit per repository)"
for repo in spexod/Portal spexod/SpExo-FrontEnd; do
    name=${repo#spexod/}
    echo; echo "==================== $repo"
    echo "--- workflow runs"
    gh run list --repo "$repo" --limit "$limit" \
        --json databaseId,number,event,headBranch,conclusion,status,createdAt,displayTitle,workflowName \
        --template '{{range .}}{{.databaseId}}  #{{.number}}  {{.conclusion}}/{{.status}}  {{.event}}  {{.headBranch}}  {{timefmt "2006-01-02 15:04" .createdAt}}  {{.workflowName}}: {{.displayTitle}}{{"\n"}}{{end}}'
    # the failed runs: jobs, failed steps, and the log of the failed steps in a file of their own
    for id in $(gh run list --repo "$repo" --limit "$limit" --json databaseId,conclusion \
                --jq '.[] | select(.conclusion=="failure") | .databaseId'); do
        echo "--- failed run $id: jobs"
        gh run view "$id" --repo "$repo" --json jobs \
            --jq '.jobs[] | "\(.name): \(.conclusion)  failed steps: \([.steps[] | select(.conclusion=="failure") | .name] | join(", "))"'
        gh run view "$id" --repo "$repo" --log-failed > "$out/$name-run-$id-failed.log" 2>&1
        echo "    log of the failed steps: $out/$name-run-$id-failed.log ($(wc -l < "$out/$name-run-$id-failed.log") lines)"
    done
    echo "--- open pull requests"
    gh pr list --repo "$repo" --state open --json number,author,headRefName,title,createdAt,statusCheckRollup \
        --template '{{range .}}#{{.number}}  {{.author.login}}  {{.headRefName}}  {{timefmt "2006-01-02" .createdAt}}  {{.title}}{{"\n"}}{{range .statusCheckRollup}}      check: {{.name}} {{.conclusion}}{{"\n"}}{{end}}{{end}}'
    echo "--- pull requests closed in the last 14 days"
    gh pr list --repo "$repo" --state closed --limit 20 --search "closed:>=$(date -u -d '14 days ago' +%Y-%m-%d 2>/dev/null || date -u -v-14d +%Y-%m-%d)" \
        --json number,author,title,mergedAt,closedAt \
        --template '{{range .}}#{{.number}}  {{.author.login}}  {{if .mergedAt}}merged{{else}}closed{{end}} {{timefmt "2006-01-02" .closedAt}}  {{.title}}{{"\n"}}{{end}}'
    echo "--- Dependabot security alerts (open)"
    gh api "repos/$repo/dependabot/alerts?state=open&per_page=50" \
        --jq '.[] | "\(.security_advisory.severity)  \(.dependency.package.ecosystem)/\(.dependency.package.name)  \(.security_advisory.ghsa_id)  \(.dependency.manifest_path)  \(.security_advisory.summary)"' \
        2>&1 | head -30
done
} | tee "$out/status.txt"
echo; echo "saved to $out/status.txt"
