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
python3 "$SCRIPT_DIR/pubmed_fetch_v2.py" "$DAYS" "$MAX_RESULTS" > "$WEEKLY_DIR/data_${DATE}.json" 2>"$WEEKLY_DIR/fetch_log_${DATE}.txt"
echo "  (Check fetch_log_${DATE}.txt for progress)"

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
    
    # Generate PDF from updated report (emoji-free with styling)
    echo "📄 Generating professional PDF..."
    REPORT_BASENAME=$(basename "$REPORT_FILE" .md)
    CLEAN_MD="$WEEKLY_DIR/${REPORT_BASENAME}_clean.md"
    HTML_FILE="$WEEKLY_DIR/${REPORT_BASENAME}_styled.html"
    PDF_FILE="$WEEKLY_DIR/${REPORT_BASENAME}.pdf"
    
    if command -v python3 &>/dev/null && python3 -c "import markdown" &>/dev/null; then
        # Step 1: Remove emojis
        python3 "$SCRIPT_DIR/strip_emojis.py" "$REPORT_FILE" > "$CLEAN_MD"
        
        # Step 2: Convert to HTML with CSS styling
        python3 << EOF
import markdown
with open('$CLEAN_MD', 'r', encoding='utf-8') as f:
    md = f.read()
html_body = markdown.markdown(md, extensions=['tables', 'fenced_code'])
html_full = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>mRNA Therapeutics Weekly Report</title>
    <link rel="stylesheet" href="report_style.css">
</head>
<body>
{html_body}
</body>
</html>
"""
with open('$HTML_FILE', 'w', encoding='utf-8') as f:
    f.write(html_full)
EOF
        
        # Step 3: Generate PDF with WeasyPrint
        if command -v weasyprint &>/dev/null; then
            weasyprint "$HTML_FILE" "$PDF_FILE" 2>/dev/null
            if [ -f "$PDF_FILE" ]; then
                echo "✅ Professional PDF generated: $(basename "$PDF_FILE")"
                git add "$PDF_FILE" 2>/dev/null || true
                rm -f "$CLEAN_MD"  # Cleanup temp file
            else
                echo "⚠️  PDF generation failed"
            fi
        else
            echo "⚠️  weasyprint not found, skipping PDF generation"
        fi
    else
        echo "⚠️  python3-markdown not found, skipping PDF generation"
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
    # Determine default branch
    DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "master")
    
    if git push origin "$DEFAULT_BRANCH" 2>&1; then
        echo "✅ Pushed to GitHub ($DEFAULT_BRANCH)"
    else
        echo "⚠️  Push failed. Check:"
        echo "   - SSH key configured? (ssh -T git@github.com)"
        echo "   - Remote URL correct? (git remote -v)"
        echo "   - Branch exists? (git branch -a)"
    fi
else
    echo "⚠️  No Git remote configured, skipping push"
    echo "   To configure: git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git"
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
