# mRNA Weekly - Automated Literature Report System

**Purpose:** Automated fetching, filtering, and reporting of mRNA therapeutics literature from multiple sources.

---

## 🚀 Quick Start

### **Fully automated workflow (with Git push):**
```bash
cd ~/.openclaw/workspace
./scripts/run_mrna_weekly.sh 7 50  # Last 7 days, max 50 articles
```

This will:
1. ✅ Fetch data from PubMed, bioRxiv, medRxiv, ClinicalTrials.gov
2. ✅ Generate complete bibliography
3. ✅ Append bibliography to existing report (if found)
4. ✅ Git commit changes
5. ✅ Git push to remote (if configured)

---

## 📁 Scripts Overview

### **1. `pubmed_fetch_v2.py`** - Data Fetcher (Core)

**Usage:**
```bash
python3 scripts/pubmed_fetch_v2.py [days] [max_results]
python3 scripts/pubmed_fetch_v2.py 14 50  # Last 14 days, max 50 results
```

**Output:** JSON to stdout with articles and clinical trials

**Features:**
- ✅ **PubMed** via Bio.Entrez with MeSH-optimized queries
- ✅ **bioRxiv/medRxiv** via parallel API requests (5 concurrent workers)
- ✅ **ClinicalTrials.gov** for trial updates
- ✅ Automatic categorization (7 categories)
- ✅ Deduplication by DOI
- ✅ Timeout handling for slow APIs

**Data Sources:**
- **PubMed:** MeSH terms + text query for precision
- **bioRxiv:** Parallel 1-day chunks (avoids timeouts)
- **medRxiv:** Same parallel approach
- **ClinicalTrials.gov:** API v2 with date filtering

**Example output structure:**
```json
{
  "fetch_date": "2026-03-16T08:00:00Z",
  "period_days": 14,
  "stats": {...},
  "articles": [...],
  "clinical_trials": [...]
}
```

---

### **2. `generate_bibliography.py`** - Bibliography Generator

**Usage:**
```bash
python3 scripts/generate_bibliography.py < data.json > bibliography.md
```

**Input:** JSON from `pubmed_fetch_v2.py`  
**Output:** Markdown bibliography (numbered list)

**Features:**
- ✅ Grouped by source (PubMed, bioRxiv, medRxiv)
- ✅ Sorted by date (newest first)
- ✅ Formatted citations with PMID/DOI links
- ✅ Author truncation (et al. for >3)
- ✅ Preprint tags

**Example output:**
```markdown
## 📚 Complete Bibliography

**Total articles screened:** 51

### PubMed (50 articles)

**1.** Smith J et al. *Novel LNP formulation for lung delivery*. J Control Release (2026). [PMID: 12345] | [DOI: 10.1016/xyz]

**2.** ...
```

---

### **3. `run_mrna_weekly.sh`** - Orchestration Script (Master)

**Usage:**
```bash
./scripts/run_mrna_weekly.sh [days] [max_results]
./scripts/run_mrna_weekly.sh 7 50
```

**Workflow:**
1. Fetch data → `mrna-weekly/data_YYYY-MM-DD.json`
2. Generate bibliography → `mrna-weekly/bibliography_YYYY-MM-DD.md`
3. Append to report (if exists)
4. Git commit
5. Git push (if remote configured)

**Configuration:**
- `DAYS` (default: 7)
- `MAX_RESULTS` (default: 50)
- Output directory: `mrna-weekly/`

---

## 🔧 Setup

### **1. Install Dependencies**

```bash
pip3 install biopython
```

### **2. Configure Git Remote (Optional)**

```bash
cd ~/.openclaw/workspace
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
```

### **3. Test Run**

```bash
# Dry run (no Git push)
python3 scripts/pubmed_fetch_v2.py 3 10 > test_data.json
python3 scripts/generate_bibliography.py < test_data.json

# Full workflow
./scripts/run_mrna_weekly.sh 3 10
```

---

## 📊 Performance

### **Timing (approximate):**

| Source | Days | Articles | Time |
|--------|------|----------|------|
| PubMed | 14 | ~50 | 10-15s |
| bioRxiv | 14 | ~5 | 60-90s (parallel) |
| medRxiv | 14 | ~2 | 30-60s (parallel) |
| ClinicalTrials.gov | 14 | ~20 | 5-10s |
| **Total** | **14** | **~77** | **~2-3 min** |

**Optimization:**
- ✅ Parallel bioRxiv requests (5 workers) → 5x faster
- ✅ 1-day chunks for bioRxiv → Avoids timeouts
- ✅ Timeout handling → Graceful degradation

---

## 🐛 Troubleshooting

### **bioRxiv timeouts:**
```bash
# Reduce days or increase timeout in pubmed_fetch_v2.py
python3 scripts/pubmed_fetch_v2.py 7 50  # Shorter period
```

### **No articles found:**
```bash
# Check BIORXIV_TERMS in pubmed_fetch_v2.py
# May need to adjust filtering keywords
```

### **Git push fails:**
```bash
# Check remote configuration
git remote -v

# Reconfigure if needed
git remote set-url origin <new-url>
```

### **Bibliography not appended:**
```bash
# Check if section already exists
grep "Complete Bibliography" mrna-weekly/mrna-weekly_*.md

# Manually append if needed
cat bibliography_2026-03-16.md >> mrna-weekly_2026-03-16.md
```

---

## 📝 Customization

### **Add new keywords:**

Edit `BIORXIV_TERMS` in `pubmed_fetch_v2.py`:
```python
BIORXIV_TERMS = [
    "mRNA therapeutics",
    "YOUR_NEW_TERM",  # Add here
]
```

### **Change categories:**

Edit `CATEGORIES` in `pubmed_fetch_v2.py`:
```python
CATEGORIES = {
    "Your New Category": ["keyword1", "keyword2"],
}
```

### **Adjust parallelism:**

In `search_biorxiv()`:
```python
with ThreadPoolExecutor(max_workers=10) as executor:  # Increase from 5
```

---

## 🔄 Automation

### **Cron job (weekly on Sunday at 9 AM):**

```bash
crontab -e
```

Add:
```cron
0 9 * * 0 cd /home/dominik/.openclaw/workspace && ./scripts/run_mrna_weekly.sh 7 50 >> /tmp/mrna_weekly_cron.log 2>&1
```

### **Manual trigger:**

```bash
./scripts/run_mrna_weekly.sh 14 100  # Last 2 weeks, max 100 articles
```

---

## 📂 Output Structure

```
mrna-weekly/
├── data_2026-03-16.json          # Raw JSON from fetch
├── bibliography_2026-03-16.md    # Generated bibliography
├── fetch_log_2026-03-16.txt      # Fetch stderr output
├── mrna-weekly_2026-03-16.md     # Main report (with appended bibliography)
└── mrna-weekly_2026-03-16.pdf    # PDF version (if generated)
```

---

## 🔗 Integration

### **With existing reports:**

```bash
# Generate data
python3 scripts/pubmed_fetch_v2.py 7 50 > data.json

# Generate bibliography
python3 scripts/generate_bibliography.py < data.json > bibliography.md

# Manually append to your report
cat bibliography.md >> your_report.md
```

### **As a Python module:**

```python
import json
from scripts.pubmed_fetch_v2 import search_pubmed, search_biorxiv

# Fetch
articles = search_pubmed(query="...", days=7, max_results=50)

# Process
for article in articles:
    print(article["title"])
```

---

## 📄 License

Part of the OpenClaw workspace. See main repository for license.

---

## 🆘 Support

- Check `fetch_log_*.txt` for errors
- Review stderr output during run
- Validate JSON structure: `python3 -m json.tool < data.json`

**Common issues:**
- Timeout → Reduce `days` parameter
- No articles → Check filtering keywords
- Git errors → Verify remote configuration
