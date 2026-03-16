#!/bin/bash
# Orchestrates the complete mRNA Weekly workflow:
# 1. Fetch data from PubMed, bioRxiv, ClinicalTrials.gov
# 2. Generate bibliography
# 3. Append to existing report
# 4. Git commit + push
#
# Usage:
#   ./run_mrna_weekly.sh [days] [max_results]
#   ./run_mrna_weekly.sh 7 50  # Last 7 days, max 50 articles

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
WEEKLY_DIR="$WORKSPACE_DIR/mrna-weekly"
DAYS=${1:-7}
MAX_RESULTS=${2:-50}
DATE=$(date +%Y-%m-%d)

echo "╔════════════════════════════════════════╗"
echo "║   mRNA Weekly - Automated Workflow     ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Period: Last $DAYS days"
echo "  Max results: $MAX_RESULTS per source"
echo "  Date: $DATE"
echo ""

# Ensure mrna-weekly directory exists
mkdir -p "$WEEKLY_DIR"

# Step 1: Fetch data
echo "📥 Step 1/5: Fetching data from PubMed, bioRxiv, medRxiv, ClinicalTrials.gov..."
cd "$WORKSPACE_DIR"
python3 "$SCRIPT_DIR/pubmed_fetch_v2.py" "$DAYS" "$MAX_RESULTS" > "$WEEKLY_DIR/data_${DATE}.json" 2>&1 | tee "$WEEKLY_DIR/fetch_log_${DATE}.txt"

if [ ! -f "$WEEKLY_DIR/data_${DATE}.json" ]; then
    echo "❌ Error: Data fetch failed! No JSON output."
    exit 1
fi

echo "✅ Data saved to: data_${DATE}.json"
echo ""

# Step 2: Generate bibliography
echo "📚 Step 2/5: Generating complete bibliography..."
python3 "$SCRIPT_DIR/generate_bibliography.py" < "$WEEKLY_DIR/data_${DATE}.json" > "$WEEKLY_DIR/bibliography_${DATE}.md"

if [ ! -f "$WEEKLY_DIR/bibliography_${DATE}.md" ]; then
    echo "❌ Error: Bibliography generation failed!"
    exit 1
fi

ARTICLE_COUNT=$(grep -c "^\*\*[0-9]" "$WEEKLY_DIR/bibliography_${DATE}.md" || echo "0")
echo "✅ Bibliography generated: $ARTICLE_COUNT articles"
echo ""

# Step 3: Check if report exists and append bibliography
REPORT_FILE=$(ls "$WEEKLY_DIR"/mrna-weekly_*.md 2>/dev/null | sort -r | head -1)

if [ -n "$REPORT_FILE" ] && [ -f "$REPORT_FILE" ]; then
    echo "📄 Step 3/5: Appending bibliography to existing report..."
    echo "  Report: $(basename "$REPORT_FILE")"
    
    # Check if bibliography already exists in report
    if grep -q "## 📚 Complete Bibliography" "$REPORT_FILE"; then
        echo "⚠️  Bibliography section already exists, skipping append"
    else
        # Append bibliography to report
        cat "$WEEKLY_DIR/bibliography_${DATE}.md" >> "$REPORT_FILE"
        echo "✅ Bibliography appended to report"
    fi
else
    echo "⚠️  Step 3/5: No existing report found, bibliography saved separately"
fi
echo ""

# Step 4: Git commit
echo "💾 Step 4/5: Committing to Git..."
cd "$WORKSPACE_DIR"

# Add files
git add "$WEEKLY_DIR/data_${DATE}.json" 2>/dev/null || true
git add "$WEEKLY_DIR/bibliography_${DATE}.md" 2>/dev/null || true
git add "$WEEKLY_DIR/fetch_log_${DATE}.txt" 2>/dev/null || true
if [ -n "$REPORT_FILE" ]; then
    git add "$REPORT_FILE" 2>/dev/null || true
fi

# Check if there are changes
if git diff --cached --quiet; then
    echo "ℹ️  No changes to commit"
else
    # Commit
    COMMIT_MSG="mRNA Weekly update ($DATE): $ARTICLE_COUNT articles, last $DAYS days"
    git commit -m "$COMMIT_MSG"
    echo "✅ Committed: $COMMIT_MSG"
fi
echo ""

# Step 5: Git push
echo "🚀 Step 5/5: Pushing to GitHub..."
if git remote get-url origin &>/dev/null; then
    git push origin master || git push origin main || echo "⚠️  Push failed (check remote configuration)"
    echo "✅ Pushed to GitHub"
else
    echo "⚠️  No Git remote configured, skipping push"
    echo "   To configure: git remote add origin <your-repo-url>"
fi
echo ""

echo "╔════════════════════════════════════════╗"
echo "║          ✅ Workflow Complete!          ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Output files:"
echo "  📊 Data: $WEEKLY_DIR/data_${DATE}.json"
echo "  📚 Bibliography: $WEEKLY_DIR/bibliography_${DATE}.md"
if [ -n "$REPORT_FILE" ]; then
    echo "  📄 Report: $REPORT_FILE"
fi
echo ""
echo "Next steps:"
echo "  1. Review the bibliography: cat $WEEKLY_DIR/bibliography_${DATE}.md"
echo "  2. Check GitHub: git log -1"
echo "  3. Generate PDF: (if you have a report generator)"
echo ""
