#!/usr/bin/env bash
# Rewrite the last N commits (or all commits if fewer exist) to remove
# Co-authored-by: cursoragent lines from commit messages. Non-interactive.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

COMMIT_COUNT="${1:-15}"
TOTAL="$(git rev-list --count HEAD)"

export FILTER_BRANCH_SQUELCH_WARNING=1

if [ "$TOTAL" -le "$COMMIT_COUNT" ]; then
  echo "Rewriting all ${TOTAL} commit(s) on $(git branch --show-current)."
  REWRITE_REVS="HEAD"
else
  echo "Rewriting the last ${COMMIT_COUNT} of ${TOTAL} commit(s) on $(git branch --show-current)."
  REWRITE_REVS="HEAD~${COMMIT_COUNT}..HEAD"
fi

git filter-branch -f --msg-filter '
  grep -vi "Co-authored-by:.*cursoragent" || true
' "$REWRITE_REVS"

# Remove backup refs created by filter-branch
git for-each-ref --format="%(refname)" refs/original/ | while read -r ref; do
  git update-ref -d "$ref"
done

echo "Done. Remaining Co-authored-by cursoragent lines in rewritten range:"
if [ "$TOTAL" -le "$COMMIT_COUNT" ]; then
  git log --format="%B" | grep -i "cursoragent" && exit 1 || echo "(none)"
else
  git log "$REWRITE_REVS" --format="%B" | grep -i "cursoragent" && exit 1 || echo "(none)"
fi
