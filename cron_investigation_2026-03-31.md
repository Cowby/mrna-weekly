# Investigation: mRNA Weekly Cron-Job Verschwunden

**Date:** 2026-03-31  
**Issue:** Automatischer wöchentlicher mRNA-Report läuft nicht mehr

---

## 🔍 Findings

### 1. Original Setup (2026-03-05)
- **Type:** OpenClaw Cron-Job (NICHT System-Cron!)
- **Job ID:** ad74eaea-b269-47e2-9223-50d175311f01
- **Schedule:** Every Monday 08:00 UTC
- **Runtime:** Isolated session with Sonnet model
- **Actions:** Fetch PubMed → JSON → Markdown → PDF → Telegram

**Source:** memory/2026-03-05.md

### 2. What Happened on March 30?
- **08:06 CET:** Data fetch ran (fetch_2026-03-30.json created)
- **BUT:** Only partial execution!
  - ✅ Data fetched (37 articles)
  - ❌ Report NOT generated
  - ❌ PDF NOT created
  - ❌ NOT sent to Telegram

**Evidence:**
```bash
ls -lh mrna-weekly/
# Last successful report: mrna-weekly_2026-03-23.pdf (March 23)
# Next attempt: fetch_2026-03-30.json (March 30, incomplete)
```

### 3. Current State
**System Crontab:**
```bash
$ crontab -l
# Only contains: Sonos Kirschkernkissen Reminder (19:50)
# mRNA job is MISSING!
```

**OpenClaw Gateway:**
- ✅ Status: Running (since March 23, 13:16 CET)
- ⚠️  Cron command fails to connect (gateway closed 1000)

### 4. Why Did It Disappear?

**Hypothesis 1: Gateway Restart (March 23)**
- Gateway restarted on March 23 at 13:16
- OpenClaw Cron-Jobs may not persist across restarts
- Job was configured in-memory, not in persistent storage

**Hypothesis 2: OpenClaw Version Update**
- OpenClaw v2026.3.2 (current version)
- Possible breaking change in cron persistence?

**Hypothesis 3: Configuration Migration**
- Moving from old cron system to new system
- Jobs not migrated automatically

---

## 🐛 Root Cause

**Most Likely:** OpenClaw Cron-Jobs are stored in **runtime state**, not persistent config files. When the gateway restarted on March 23, the job was lost.

**Evidence:**
1. Gateway uptime: "since Mon 2026-03-23 13:16:08"
2. Last successful report: March 23 (before restart)
3. March 30 fetch ran partially (orphaned process?)

---

## ✅ Solution

**Option A: System Cron (Recommended)**
- Use native Linux cron (`crontab -e`)
- More reliable, persists across restarts
- Simpler (no gateway dependency)

**Option B: OpenClaw Cron (Current System)**
- Re-create the OpenClaw cron job
- But: May disappear again on next restart
- Requires persistent config file

**Option C: Hybrid**
- System cron triggers OpenClaw agent
- Agent runs the workflow
- Best of both worlds

---

## 📋 Next Steps

1. ✅ Manual report generated (2026-03-30)
2. ⬜ Set up System Cron-Job (persistent!)
3. ⬜ Document new setup
4. ⬜ Test next Monday (April 7)

---

## 🔧 Proposed System Cron

```bash
# Add to crontab -e:
# mRNA Weekly Report - Every Monday 08:00 CET
0 8 * * 1 cd /home/dominik/.openclaw/workspace && /home/dominik/.openclaw/workspace/scripts/run_mrna_weekly.sh 7 50 >> /home/dominik/.openclaw/workspace/mrna-weekly/cron.log 2>&1
```

**Why System Cron?**
- ✅ Persists across gateway restarts
- ✅ No dependency on OpenClaw gateway
- ✅ Standard Linux cron reliability
- ✅ Easy to debug (cron.log)
- ❌ No isolated session (runs in user context)
- ❌ No automatic Telegram sending (must add to script)

---

## 📝 Lessons Learned

1. **OpenClaw Cron-Jobs are ephemeral** (runtime state, not config)
2. **Gateway restarts wipe jobs** (need persistent storage)
3. **System cron is more reliable** for production workflows
4. **Always log to file** for debugging

---

## 🎯 Recommendation

**Use System Cron + OpenClaw Agent for Telegram delivery:**

1. System cron runs `run_mrna_weekly.sh` (reliable trigger)
2. Script generates report + PDF
3. Script calls `openclaw sessions spawn` to send Telegram message
4. Best of both worlds: reliability + OpenClaw features

