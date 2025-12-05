# Quick Resume Guide

## Current Status: BLOCKED by GitHub Rate Limit

**Rate limit resets**: December 4, 2025 at 22:42:29 (~20 min from report creation)

## What's Done

- ✅ Strapi profile exists (`StrapiStrapiMain`)
- ✅ Appsmith profile created (`AppsmithorgAppsmith7046aeb3`)
- ✅ Relaxed filtering scripts created
- ✅ 2 strapi PRs filtered (strict criteria)
- ✅ 10 strapi instances already exist (from previous run)

## What's Next

### Step 1: Check Rate Limit (NOW)

```bash
curl -s https://api.github.com/rate_limit | grep remaining
```

If `remaining: 0`, wait until 22:42:29.

### Step 2: Batch Filter All Cached PRs (30-60 min)

```bash
cd /Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith
source .venv/bin/activate
python3 batch_filter_all_repos.py
```

This will process 10+ repos worth of cached PR data and create filtered outputs in `logs/prs_filtered_relaxed/`.

### Step 3: Collect Appsmith PRs (15-30 min)

```bash
python3 filter_and_collect_prs.py
```

This will collect 20+ appsmith PRs with relaxed criteria.

### Step 4: Verify Results

```bash
# Count total filtered PRs
wc -l logs/prs_filtered_relaxed/*.jsonl

# Should show 40+ PRs total
```

## Expected Output

```
strapi_strapi_relaxed.jsonl:        10-15 lines
payloadcms_payload_relaxed.jsonl:   8-12 lines
marked_marked_relaxed.jsonl:        12-18 lines
appsmith_filtered.jsonl:            10-15 lines
... (other repos)
TOTAL: 40+ PRs
```

## If You Need to Set GitHub Token

```bash
export GITHUB_TOKEN=ghp_your_personal_access_token
```

Then re-run the scripts. This increases rate limit from 60/hour to 5000/hour.

## Files Created This Session

1. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/filter_and_collect_prs.py`
2. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/batch_filter_all_repos.py`
3. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/strapi-filtered.jsonl`
4. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/SUBAGENT_REPORT.md`
5. Updated `swesmith/profiles/typescript.py` (added Appsmith profile)

## Key Decisions Made

1. **Relaxed filtering criteria** per Megathink directive:
   - Allow e2e tests (treat as unit tests)
   - Allow up to 10 files (was 5)
   - Allow up to 1000 changes (was 500)

2. **Focus on batch processing** existing cached PR data from 10+ repos

3. **Profile configuration** for Appsmith:
   - Working directory: `/testbed/app/client`
   - Test command: `pnpm test -- --run`
   - Node heap: 8GB
   - Timeout: 30 min

## Troubleshooting

### If batch_filter_all_repos.py fails with rate limit:
- Wait and retry
- Or set GITHUB_TOKEN

### If no PRs pass filters:
- Check logs/prs/ to ensure cache files exist
- Relax criteria further (edit is_good_pr_candidate_relaxed function)

### If appsmith collection fails:
- Repo might have unusual structure
- Check if PRs exist: `https://github.com/appsmithorg/appsmith/pulls?q=is%3Apr+is%3Amerged`

## Next Session Commands

After collecting 40+ PRs:

```bash
# Create task instances
python3 create_task_instances.py

# Run PR mirroring with LLM
python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/NEW_INSTANCES.jsonl \
    --model anthropic/claude-opus-4-5-20251101

# Validate
python -m swesmith.harness.valid logs/task_insts/NEW_PATCHES.json -w 1
```

## Contact Info

**Working Directory**: `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith`

**Repos Assigned**: strapi/strapi, appsmithorg/appsmith

**Goal**: 40+ filtered PRs ready for PR mirroring

**Status**: Ready to proceed once rate limit resets
