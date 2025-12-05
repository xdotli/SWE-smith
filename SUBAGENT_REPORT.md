# Subagent Report: Strapi & Appsmith PR Collection

**Date**: December 4, 2025
**Assigned Repos**: strapi/strapi, appsmithorg/appsmith
**Goal**: Collect 40+ PRs total with strict filtering criteria for fail-to-pass generation

---

## Summary

### Achievements

1. **Strapi Profile**: Already exists as `StrapiStrapiMain` in `swesmith/profiles/typescript.py`
2. **Appsmith Profile**: Created `AppsmithorgAppsmith7046aeb3` with proper configuration
3. **Filtering Scripts**: Created two scripts with relaxed criteria per Megathink directive
4. **Existing Data**: Discovered 10 strapi task instances already generated

### Challenges

1. **GitHub Rate Limit**: Hit 60/hour unauthenticated rate limit during PR collection
2. **Strict Criteria**: Initial strict filtering (must have .test.ts, <5KB, <=5 files) yielded only 2 strapi PRs
3. **No GitHub Token**: No GITHUB_TOKEN found in environment, limiting API calls to 60/hour

---

## Current Status

### Strapi Repository

| Metric | Count | Notes |
|--------|-------|-------|
| PRs in cache | 51 | In `logs/prs/strapi-prs.jsonl` |
| Strict filtered PRs | 2 | Only 2 passed original criteria |
| Existing task instances | 10 | In `logs/tasks/strapi-insts.jsonl` |
| Existing bug patches | 10 | In `logs/task_insts/strapi_patches.json` |

**Filtered PRs (Strict Criteria)**:
1. PR #24821: "fix: bulk unpublish when creating a new locale" (110 changes, 3 files)
2. PR #24805: "fix: show relations per locale in listview" (214 changes, 2 files)

### Appsmith Repository

| Metric | Count | Notes |
|--------|-------|-------|
| Profile created | Yes | `AppsmithorgAppsmith7046aeb3` |
| PRs collected | 0 | Rate limit hit before collection started |
| Docker image | Not built | Pending PR collection |

---

## Files Created

### 1. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/filter_and_collect_prs.py`

**Purpose**: Filter existing strapi PRs and collect new appsmith PRs
**Status**: Partially executed (strapi done, appsmith blocked by rate limit)
**Criteria**: Relaxed per Megathink directive
- Allow e2e tests (treat as unit tests)
- Allow up to 10 files changed
- Allow up to 1000 changes (~10KB)
- Include test files with patterns: .test., .spec., test/, tests/, e2e/

### 2. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/batch_filter_all_repos.py`

**Purpose**: Batch process ALL existing PR cache files with relaxed criteria
**Status**: Ready to run once rate limit resets
**Repos Covered**:
- strapi/strapi
- payloadcms/payload
- excalidraw/excalidraw
- markedjs/marked
- iamkun/dayjs
- axios/axios
- colinhacks/zod
- lodash/lodash
- date-fns/date-fns
- tj/commander.js

### 3. `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/strapi-filtered.jsonl`

**Purpose**: Strictly filtered strapi PRs
**Status**: Complete (2 PRs)
**Format**: JSONL with full PR metadata including file lists

### 4. Updated `swesmith/profiles/typescript.py`

**Change**: Added `AppsmithorgAppsmith7046aeb3` profile
**Configuration**:
- Commit: `7046aeb3`
- Test command: `cd app/client && pnpm test -- --run`
- Timeout: 1800s (30 min)
- Node heap: 8GB
- Platform: linux/x86_64

---

## GitHub Rate Limit Issue

### Current Status
```
Limit: 60/hour (unauthenticated)
Remaining: 0
Reset time: 2025-12-04 22:42:29 (~20 minutes from report time)
```

### Solution Options

1. **Wait for reset** (20 minutes)
2. **Set GITHUB_TOKEN** for 5000/hour limit
3. **Use existing cached PR data** for batch filtering

---

## Next Steps (Priority Order)

### Immediate (Once Rate Limit Resets)

1. **Run batch filtering** on all existing PR cache:
   ```bash
   cd /Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith
   source .venv/bin/activate
   python3 batch_filter_all_repos.py
   ```

   **Expected output**: 20-40 filtered PRs across all repos

2. **Collect appsmith PRs** with relaxed criteria:
   ```bash
   python3 filter_and_collect_prs.py
   ```

   **Target**: 20+ appsmith PRs

### Short-term (After Collection)

3. **Create task instances** for newly filtered PRs:
   ```bash
   # For strapi (using existing profile)
   python3 create_strapi_instances.py

   # For appsmith (new profile)
   python3 create_appsmith_instances.py
   ```

4. **Run PR mirroring** with LLM (Claude Opus 4.5):
   ```bash
   python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/strapi-relaxed-insts.jsonl \
       --model anthropic/claude-opus-4-5-20251101

   python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/appsmith-insts.jsonl \
       --model anthropic/claude-opus-4-5-20251101
   ```

5. **Validate instances**:
   ```bash
   python -m swesmith.harness.valid logs/task_insts/strapi_relaxed_patches.json -w 1
   python -m swesmith.harness.valid logs/task_insts/appsmith_patches.json -w 1
   ```

---

## Expected Outcomes

### Conservative Estimate

| Stage | Strapi | Appsmith | Total |
|-------|--------|----------|-------|
| PRs collected | 51 cached | 25 new | 76 |
| After relaxed filter | 10-15 | 8-10 | 18-25 |
| LLM reversal success (60%) | 6-9 | 5-6 | 11-15 |
| Validation pass (50%) | 3-5 | 2-3 | 5-8 |

### Optimistic Estimate

| Stage | Strapi | Appsmith | Total |
|-------|--------|----------|-------|
| PRs collected (batch all repos) | 100+ | 30 | 130+ |
| After relaxed filter | 30+ | 10+ | 40+ |
| LLM reversal success (60%) | 18+ | 6+ | 24+ |
| Validation pass (50%) | 9+ | 3+ | 12+ |

---

## Recommendations

### For Immediate Action

1. **Set GITHUB_TOKEN** to avoid rate limits:
   ```bash
   export GITHUB_TOKEN=ghp_your_token_here
   ```

2. **Focus on batch filtering first** since we have 10+ repos worth of cached PR data

3. **Prioritize repos with best test coverage**:
   - marked (markdown parser with excellent tests)
   - zod (TypeScript schema validation)
   - dayjs (date library with extensive tests)
   - strapi (CMS with API tests)

### For Long-term Success

1. **Relax criteria further** if 40+ target not met:
   - Allow up to 15 files changed
   - Allow up to 1500 changes (~15KB)

2. **Add more repos** from the curated list:
   - tldraw (similar to excalidraw)
   - medusa (already has profile)
   - hoppscotch (API testing tool)
   - nocodb (no-code database)

3. **Parallelize validation** with higher worker count:
   ```bash
   python -m swesmith.harness.valid PATCHES.json -w 4
   ```

---

## Cost Estimate

### LLM Calls (Claude Opus 4.5)

| Scenario | Instances | Cost per Instance | Total Cost |
|----------|-----------|-------------------|------------|
| Conservative | 18-25 | $0.055 | $1-1.40 |
| Optimistic | 40+ | $0.055 | $2.20+ |

### Docker Builds

- Appsmith image: ~5-10GB, 3-5 min build time
- One-time cost (reused for all instances)

---

## Blockers

1. **GitHub Rate Limit**: ⚠️ CRITICAL - Must wait 20 min or set token
2. **Appsmith Repo Structure**: ⚠️ MEDIUM - Need to verify test command works
3. **Test Coverage**: ⚠️ MEDIUM - Repos may lack sufficient unit tests

---

## Files to Monitor

```
/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/
├── logs/
│   ├── prs/                              # PR cache (51-200 PRs per repo)
│   ├── prs_filtered_relaxed/             # Filtered output (will be created)
│   ├── tasks/                            # Task instances for PR mirroring
│   ├── task_insts/                       # Generated bug patches
│   └── bug_gen/                          # LLM reversal output
├── filter_and_collect_prs.py            # Main filtering script
├── batch_filter_all_repos.py            # Batch processing script
└── swesmith/profiles/typescript.py      # Profiles (updated with Appsmith)
```

---

## Contact/Handoff Notes

**Current Working Directory**: `/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith`

**Virtual Environment**: `.venv/` (already activated)

**Key Commands**:
```bash
# Check rate limit
curl -s https://api.github.com/rate_limit | python3 -m json.tool

# Activate venv
source .venv/bin/activate

# Run batch filtering
python3 batch_filter_all_repos.py

# Collect appsmith PRs
python3 filter_and_collect_prs.py
```

**GITHUB_TOKEN Setup** (if available):
```bash
export GITHUB_TOKEN=ghp_your_token_here
# Then re-run scripts
```

---

## Conclusion

We have successfully:
1. Created appsmith profile
2. Developed relaxed filtering scripts
3. Identified existing strapi data (10 instances)
4. Set up batch processing pipeline

**Status**: Blocked by GitHub rate limit, ready to proceed in 20 minutes.

**Expected Timeline**:
- Batch filtering: 30-60 min (after rate limit resets)
- PR collection: 15-30 min
- Task instance creation: 5-10 min
- LLM reversal: 20-40 min (depending on instance count)
- Validation: 30-60 min per batch

**Total estimated time to completion**: 2-3 hours after rate limit resets.
