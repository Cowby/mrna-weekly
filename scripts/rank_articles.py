#!/usr/bin/env python3
"""Rank articles by relevance using multiple criteria.

Scoring factors:
- Recency (newer = higher)
- Category relevance (core categories weighted higher)
- Impact indicators (keywords, novelty)
- Source credibility (PubMed > bioRxiv > medRxiv)
- Journal prestige (Nature, JACS, etc. weighted higher)
"""

import json
import sys
from datetime import datetime
from typing import Dict, List

# Category weights (higher = more important to mRNA therapeutics)
CATEGORY_WEIGHTS = {
    "LNP Engineering & Delivery": 1.0,
    "Vaccines": 0.9,
    "Cancer & Immunotherapy": 0.95,
    "Clinical Development": 0.9,
    "RNA Biology & Design": 0.85,
    "Protein Replacement & Gene Therapy": 0.85,
    "Manufacturing & Analytics": 0.75,
    "Other": 0.5,
}

# High-impact keywords (presence increases score)
IMPACT_KEYWORDS = [
    "breakthrough", "novel", "first", "innovative", "precision", "targeted",
    "clinical trial", "phase", "fda", "approval", "efficacy", "safety",
    "crispr", "base edit", "prime edit", "self-amplifying", "saRNA",
    "organ-specific", "tissue-specific", "biodistribution", "targeting",
    "nanoparticle engineering", "ionizable lipid", "peg lipid",
]

# High-prestige journals (exact match or contains)
PRESTIGE_JOURNALS = {
    "Nature": 1.3,
    "Science": 1.3,
    "Cell": 1.3,
    "NEJM": 1.25,
    "Lancet": 1.25,
    "JACS": 1.2,
    "Molecular Therapy": 1.15,
    "Journal of Controlled Release": 1.1,
}


def score_article(article: Dict, current_date: str = None) -> float:
    """Calculate relevance score for an article.
    
    Returns score between 0-100.
    """
    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")
    
    score = 0.0
    
    # 1. Recency score (max 25 points)
    date_str = article.get("date", "2000-01-01")
    try:
        article_date = datetime.fromisoformat(date_str.split()[0])
        current_dt = datetime.fromisoformat(current_date)
        days_old = (current_dt - article_date).days
        
        # Exponential decay: max score for today, halves every 7 days
        recency_score = 25 * (0.5 ** (days_old / 7.0))
        score += recency_score
    except:
        score += 0  # Invalid date = 0 points
    
    # 2. Category relevance (max 25 points)
    categories = article.get("categories", [])
    if categories:
        avg_weight = sum(CATEGORY_WEIGHTS.get(cat, 0.5) for cat in categories) / len(categories)
        score += avg_weight * 25
    
    # 3. Impact indicators from title/abstract (max 25 points)
    text = (article.get("title", "") + " " + article.get("abstract", "")).lower()
    keyword_matches = sum(1 for kw in IMPACT_KEYWORDS if kw in text)
    impact_score = min(keyword_matches * 2.5, 25)  # Max 10 keywords
    score += impact_score
    
    # 4. Journal prestige (max 15 points)
    journal = article.get("journal", "")
    prestige_multiplier = 1.0
    for prestige_journal, multiplier in PRESTIGE_JOURNALS.items():
        if prestige_journal.lower() in journal.lower():
            prestige_multiplier = multiplier
            break
    score += (prestige_multiplier - 1.0) * 50  # Convert to 0-15 range
    
    # 5. Source credibility (max 10 points)
    source = article.get("source", "")
    if source == "pubmed":
        score += 10
    elif source == "biorxiv":
        score += 8  # Preprints slightly lower
    elif source == "medrxiv":
        score += 7
    
    return min(score, 100.0)  # Cap at 100


def rank_articles(data: Dict) -> List[Dict]:
    """Rank all articles by relevance score."""
    articles = data.get("articles", [])
    
    # Score each article
    for article in articles:
        article["relevance_score"] = score_article(article)
    
    # Sort by score (descending)
    ranked = sorted(articles, key=lambda x: x["relevance_score"], reverse=True)
    
    return ranked


def print_top_articles(ranked_articles: List[Dict], top_n: int = 20):
    """Print top N articles with scores."""
    print(f"=== Top {top_n} Articles by Relevance Score ===\n")
    
    for i, article in enumerate(ranked_articles[:top_n], 1):
        score = article["relevance_score"]
        title = article["title"]
        source = article["source"]
        journal = article.get("journal", "N/A")
        date = article.get("date", "N/A")
        categories = article.get("categories", [])
        
        # Star rating (3 stars for score > 70, 2 stars for > 55, 1 star otherwise)
        if score >= 70:
            stars = "⭐⭐⭐"
        elif score >= 55:
            stars = "⭐⭐"
        else:
            stars = "⭐"
        
        print(f"{i}. {title} {stars}")
        print(f"   Score: {score:.1f} | Source: {source} | Date: {date}")
        print(f"   Journal: {journal}")
        print(f"   Categories: {', '.join(categories)}")
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    
    ranked = rank_articles(data)
    
    # Print top 20
    print_top_articles(ranked, top_n=20)
    
    # Export ranked data
    data["articles"] = ranked
    with open("ranked_articles.json", 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ Ranked {len(ranked)} articles saved to ranked_articles.json")
