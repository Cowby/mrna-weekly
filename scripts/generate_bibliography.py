#!/usr/bin/env python3
"""Generate complete bibliography section from mRNA weekly JSON data.

Reads JSON from stdin and outputs formatted markdown bibliography to stdout.
"""

import json
import sys
from datetime import datetime


def format_authors(authors: list[str]) -> str:
    """Format author list with et al. if >3."""
    if not authors:
        return "Unknown Authors"
    if len(authors) <= 3:
        return ", ".join(authors)
    return f"{authors[0]} et al."


def format_article(article: dict, index: int) -> str:
    """Format single article as numbered bibliography entry."""
    title = article.get("title", "Untitled")
    authors = format_authors(article.get("authors", []))
    journal = article.get("journal", "Unknown Journal")
    date = article.get("date", "")
    pmid = article.get("pmid", "")
    doi = article.get("doi", "")
    source = article.get("source", "unknown")
    
    # Parse date for year
    year = ""
    if date:
        try:
            if "-" in date:
                year = date.split("-")[0]
            elif " " in date:
                year = date.split()[-1]
        except:
            year = ""
    
    # Build citation
    citation = f"**{index}.** {authors}. *{title}*. {journal}"
    if year:
        citation += f" ({year})"
    citation += "."
    
    # Add identifiers
    identifiers = []
    if pmid:
        identifiers.append(f"[PMID: {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)")
    if doi:
        identifiers.append(f"[DOI: {doi}](https://doi.org/{doi})")
    
    if identifiers:
        citation += " " + " | ".join(identifiers)
    
    # Add source tag
    if source in ["biorxiv", "medrxiv"]:
        citation += " *[Preprint]*"
    
    return citation


def generate_bibliography(data: dict) -> str:
    """Generate complete bibliography section."""
    articles = data.get("articles", [])
    trials = data.get("clinical_trials", [])
    stats = data.get("stats", {})
    fetch_date = data.get("fetch_date", "")
    
    # Parse fetch date
    try:
        fetch_dt = datetime.fromisoformat(fetch_date.replace("Z", "+00:00"))
        fetch_str = fetch_dt.strftime("%B %d, %Y %H:%M UTC")
    except:
        fetch_str = fetch_date
    
    # Header
    md = "---\n\n"
    md += "## 📚 Complete Bibliography\n\n"
    md += f"**Total articles screened:** {len(articles)}  \n"
    md += f"**Generated:** {fetch_str}  \n\n"
    
    # Group by source
    by_source = {}
    for a in articles:
        src = a.get("source", "unknown")
        by_source.setdefault(src, []).append(a)
    
    # Sort sources: PubMed first, then alphabetically
    source_order = ["pubmed", "biorxiv", "medrxiv"]
    other_sources = sorted(set(by_source.keys()) - set(source_order))
    
    total_idx = 1
    
    for source in source_order + other_sources:
        if source not in by_source:
            continue
        
        source_articles = by_source[source]
        source_name = {
            "pubmed": "PubMed",
            "biorxiv": "bioRxiv Preprints",
            "medrxiv": "medRxiv Preprints"
        }.get(source, source.capitalize())
        
        md += f"### {source_name} ({len(source_articles)} articles)\n\n"
        
        # Sort by date (newest first)
        sorted_articles = sorted(
            source_articles,
            key=lambda x: x.get("date", "1900-01-01"),
            reverse=True
        )
        
        for article in sorted_articles:
            md += format_article(article, total_idx) + "\n\n"
            total_idx += 1
    
    # Clinical trials summary
    if trials:
        md += f"### Clinical Trial Updates ({len(trials)} trials)\n\n"
        md += "*Clinical trial records tracked separately. See ClinicalTrials.gov section above for details.*\n\n"
    
    return md


def main():
    """Read JSON from stdin and output markdown bibliography."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        return 1
    
    bibliography = generate_bibliography(data)
    print(bibliography)
    return 0


if __name__ == "__main__":
    sys.exit(main())
