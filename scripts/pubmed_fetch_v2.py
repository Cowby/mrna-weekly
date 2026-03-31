#!/usr/bin/env python3
"""Enhanced mRNA therapeutics literature fetcher - FIXED bioRxiv timeouts.

Changes in this version:
- Increased timeout from 60s → 120s
- Reduced parallel workers from 5 → 3 (less aggressive)
- Added retry mechanism (2 retries per request)
- Better error handling
"""

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ── Bio.Entrez (PubMed) ──────────────────────────────────────────────

from Bio import Entrez, Medline

Entrez.email = "openclaw-agent@example.com"
Entrez.tool = "mrna-weekly-report"

# MeSH-optimized query for mRNA therapeutics
PUBMED_QUERY = (
    '('
    '"RNA, Messenger"[MeSH] OR "mRNA"[tiab] OR "messenger RNA"[tiab]'
    ') AND ('
    '"Nanoparticles"[MeSH] OR "Lipid Nanoparticles"[tiab] OR "LNP"[tiab] '
    'OR "Drug Delivery Systems"[MeSH] OR "Therapeutics"[MeSH] '
    'OR "Vaccines, Synthetic"[MeSH] OR "mRNA vaccine"[tiab] '
    'OR "self-amplifying RNA"[tiab] OR "saRNA"[tiab] '
    'OR "circular RNA therapeutic"[tiab] OR "circRNA"[tiab] '
    'OR "nucleoside-modified"[tiab] OR "modified mRNA"[tiab] '
    'OR "RNA therapy"[tiab] OR "mRNA therapeutics"[tiab] '
    'OR "ionizable lipid"[tiab] OR "mRNA delivery"[tiab]'
    ')'
)

# Categories for automatic classification
CATEGORIES = {
    "LNP Engineering & Delivery": [
        "lipid nanoparticle", "LNP", "ionizable lipid", "delivery system",
        "nanoparticle", "formulation", "endosomal escape", "biodistribution",
        "targeting", "PEG", "cholesterol", "helper lipid", "mLNP",
        "extracellular vesicle", "exosome"
    ],
    "Vaccines": [
        "vaccine", "immunization", "antigen", "adjuvant", "booster",
        "neutralizing antibody", "T cell response", "immunogenicity",
        "seroconversion", "epitope"
    ],
    "Cancer & Immunotherapy": [
        "cancer", "tumor", "oncology", "CAR-T", "CAR T", "immunotherapy",
        "checkpoint", "neoantigen", "personalized", "TNBC", "melanoma",
        "PD-L1", "PD-1"
    ],
    "Protein Replacement & Gene Therapy": [
        "protein replacement", "gene therapy", "gene editing", "CRISPR",
        "base editing", "prime editing", "enzyme replacement", "genetic disease",
        "inherited", "metabolic disorder", "rare disease"
    ],
    "RNA Biology & Design": [
        "UTR", "codon optimization", "pseudouridine", "N1-methylpseudouridine",
        "cap analog", "poly(A)", "circular RNA", "self-amplifying", "saRNA",
        "replicon", "stability", "translation efficiency", "degradation"
    ],
    "Clinical Development": [
        "clinical trial", "phase I", "phase II", "phase III", "patient",
        "safety", "efficacy", "adverse event", "pharmacokinetics",
        "pharmacodynamics", "dose-finding", "first-in-human"
    ],
    "Manufacturing & Analytics": [
        "manufacturing", "GMP", "scale-up", "quality", "analytics",
        "characterization", "impurity", "adduct", "cold chain", "stability",
        "lyophilization", "CMC", "process development"
    ],
}


def search_pubmed(query: str, days: int = 14, max_results: int = 50) -> list[dict]:
    """Search PubMed using Bio.Entrez with MeSH-optimized query."""
    today = datetime.now(timezone.utc)
    mindate = (today - timedelta(days=days)).strftime("%Y/%m/%d")
    maxdate = today.strftime("%Y/%m/%d")

    # Search
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="relevance",
        datetype="pdat",
        mindate=mindate,
        maxdate=maxdate,
    )
    search_results = Entrez.read(handle)
    handle.close()
    pmids = search_results.get("IdList", [])

    if not pmids:
        return []

    # Fetch details using Medline format (much cleaner parsing)
    handle = Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        rettype="medline",
        retmode="text",
    )
    records = list(Medline.parse(handle))
    handle.close()

    articles = []
    for rec in records:
        pmid = rec.get("PMID", "")
        title = rec.get("TI", "")
        abstract = rec.get("AB", "")
        authors = rec.get("AU", [])
        journal = rec.get("JT", rec.get("TA", ""))
        date = rec.get("DP", "")
        doi = ""
        # Extract DOI from AID field
        for aid in rec.get("AID", []):
            if aid.endswith("[doi]"):
                doi = aid.replace(" [doi]", "")
                break

        # Mesh terms
        mesh = rec.get("MH", [])

        # Publication type
        pub_types = rec.get("PT", [])

        # Categorize
        categories = categorize_article(title, abstract)

        articles.append({
            "source": "pubmed",
            "pmid": pmid,
            "title": title,
            "authors": authors[:6],
            "journal": journal,
            "date": date,
            "doi": doi,
            "abstract": abstract,
            "mesh_terms": mesh,
            "pub_types": pub_types,
            "categories": categories,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return articles


# ── bioRxiv / medRxiv ────────────────────────────────────────────────

BIORXIV_TERMS = [
    "mRNA therapeutics", "mRNA vaccine", "lipid nanoparticle",
    "mRNA delivery", "self-amplifying RNA", "ionizable lipid",
    "mRNA-LNP", "nucleoside-modified mRNA"
]


def _fetch_biorxiv_day_with_retry(server: str, date_str: str, max_retries: int = 2) -> tuple[str, list[dict]]:
    """Fetch bioRxiv data for a single day with retry logic."""
    url = f"https://api.biorxiv.org/details/{server}/{date_str}/{date_str}/0/json"
    
    for attempt in range(max_retries + 1):
        try:
            # Longer timeout: 120 seconds (was 60)
            with urllib.request.urlopen(url, timeout=120) as r:
                data = json.loads(r.read())
            
            collection = data.get("collection", [])
            articles = []
            
            for item in collection:
                title = item.get("title", "")
                abstract = item.get("abstract", "")
                text = (title + " " + abstract).lower()
                
                # Filter for mRNA relevance
                if any(term.lower() in text for term in BIORXIV_TERMS):
                    categories = categorize_article(title, abstract)
                    doi = item.get("doi", "")
                    
                    articles.append({
                        "source": server,
                        "pmid": None,
                        "title": title,
                        "authors": parse_biorxiv_authors(item.get("authors", "")),
                        "journal": f"{server} (Preprint)",
                        "date": item.get("date", ""),
                        "doi": doi,
                        "abstract": abstract,
                        "mesh_terms": [],
                        "pub_types": ["Preprint"],
                        "categories": categories,
                        "url": f"https://doi.org/{doi}" if doi else "",
                    })
            
            # Success!
            if articles:
                print(f"  ✓ {server} {date_str}: {len(articles)} articles", file=sys.stderr)
            return (date_str, articles)
        
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                print(f"  ⚠ {server} {date_str} attempt {attempt + 1}/{max_retries + 1} failed ({e}), retrying in {wait_time}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                print(f"  ✗ {server} {date_str} failed after {max_retries + 1} attempts: {e}", file=sys.stderr)
                return (date_str, [])


def search_biorxiv(days: int = 14, max_results: int = 30, server: str = "biorxiv") -> list[dict]:
    """Search bioRxiv/medRxiv for recent preprints via the API.
    
    Uses parallel requests (ThreadPoolExecutor) with retry logic.
    Reduced from 5 → 3 parallel workers to be less aggressive.
    """
    today = datetime.now(timezone.utc)
    num_days = min(days, 14)  # Limit to 14 days max
    
    # Generate list of dates to fetch
    dates_to_fetch = [
        (today - timedelta(days=i + 1)).strftime("%Y-%m-%d")
        for i in range(num_days)
    ]
    
    # Fetch in parallel (reduced from 5 → 3 workers)
    articles = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        futures = {
            executor.submit(_fetch_biorxiv_day_with_retry, server, date_str): date_str
            for date_str in dates_to_fetch
        }
        
        # Collect results as they complete
        for future in as_completed(futures):
            date_str = futures[future]
            try:
                _, day_articles = future.result()
                articles.extend(day_articles)
            except Exception as e:
                print(f"  ✗ {server} {date_str} exception: {e}", file=sys.stderr)
    
    return articles[:max_results]


def parse_biorxiv_authors(authors_str: str) -> list[str]:
    """Parse bioRxiv author string into list."""
    if not authors_str:
        return []
    return [a.strip() for a in authors_str.split(";") if a.strip()][:6]


# ── ClinicalTrials.gov ───────────────────────────────────────────────

def search_clinical_trials(days: int = 14, max_results: int = 20) -> list[dict]:
    """Search ClinicalTrials.gov for new mRNA-related studies."""
    today = datetime.now(timezone.utc)
    min_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")

    params = urllib.parse.urlencode({
        "query.term": "mRNA OR messenger RNA OR lipid nanoparticle",
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{min_date},MAX]",
        "pageSize": max_results,
        "format": "json",
        "fields": "NCTId,BriefTitle,OverallStatus,Phase,Condition,InterventionName,StartDate,LeadSponsorName,BriefSummary",
    })
    url = f"https://clinicaltrials.gov/api/v2/studies?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "mrna-weekly-report/2.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"ClinicalTrials.gov API error: {e}", file=sys.stderr)
        return []

    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        conditions = proto.get("conditionsModule", {})
        interventions = proto.get("armsInterventionsModule", {})
        sponsor = proto.get("sponsorCollaboratorsModule", {})
        desc = proto.get("descriptionModule", {})

        nct_id = ident.get("nctId", "")
        phases = design.get("phases", [])

        # Get intervention names
        intervention_names = []
        for interv in interventions.get("interventions", []):
            intervention_names.append(interv.get("name", ""))

        trials.append({
            "source": "clinicaltrials",
            "nct_id": nct_id,
            "title": ident.get("briefTitle", ""),
            "status": status.get("overallStatus", ""),
            "phase": ", ".join(phases) if phases else "N/A",
            "conditions": conditions.get("conditions", []),
            "interventions": intervention_names,
            "sponsor": sponsor.get("leadSponsor", {}).get("name", ""),
            "summary": desc.get("briefSummary", ""),
            "url": f"https://clinicaltrials.gov/study/{nct_id}",
        })

    return trials


# ── Categorization ───────────────────────────────────────────────────

def categorize_article(title: str, abstract: str) -> list[str]:
    """Assign categories based on title + abstract keywords."""
    text = (title + " " + abstract).lower()
    matched = []
    for category, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score >= 2:
            matched.append(category)
    # Default category if nothing matched
    if not matched:
        matched.append("Other")
    return matched


# ── Statistics ───────────────────────────────────────────────────────

def compute_stats(articles: list[dict], trials: list[dict]) -> dict:
    """Compute summary statistics for the report."""
    # Category distribution
    cat_counts = {}
    for a in articles:
        for c in a.get("categories", []):
            cat_counts[c] = cat_counts.get(c, 0) + 1

    # Source distribution
    source_counts = {}
    for a in articles:
        src = a["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    # Journal distribution (top 10)
    journal_counts = {}
    for a in articles:
        j = a.get("journal", "Unknown")
        if j:
            journal_counts[j] = journal_counts.get(j, 0) + 1
    top_journals = sorted(journal_counts.items(), key=lambda x: -x[1])[:10]

    # Trial phases
    phase_counts = {}
    for t in trials:
        p = t.get("phase", "N/A")
        phase_counts[p] = phase_counts.get(p, 0) + 1

    return {
        "total_articles": len(articles),
        "total_trials": len(trials),
        "by_category": dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
        "by_source": source_counts,
        "top_journals": dict(top_journals),
        "trial_phases": phase_counts,
    }


# ── Main ─────────────────────────────────────────────────────────────

def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    print(f"╔══ mRNA Weekly Report Data Fetch (FIXED) ══╗", file=sys.stderr)
    print(f"║ Period: last {days} days", file=sys.stderr)
    print(f"║ Max results per source: {max_results}", file=sys.stderr)
    print(f"║ bioRxiv timeout: 120s (was 60s)", file=sys.stderr)
    print(f"║ Parallel workers: 3 (was 5)", file=sys.stderr)
    print(f"║ Retry logic: 2 retries per request", file=sys.stderr)
    print(f"╚═══════════════════════════════════════════╝", file=sys.stderr)

    # 1. PubMed (MeSH-optimized)
    print(f"\n📚 Searching PubMed (Bio.Entrez + MeSH)...", file=sys.stderr)
    pubmed_articles = search_pubmed(PUBMED_QUERY, days=days, max_results=max_results)
    print(f"   Found {len(pubmed_articles)} PubMed articles", file=sys.stderr)

    # 2. bioRxiv preprints
    print(f"\n📄 Searching bioRxiv preprints...", file=sys.stderr)
    biorxiv_articles = search_biorxiv(days=days, max_results=30, server="biorxiv")
    print(f"   Found {len(biorxiv_articles)} bioRxiv preprints", file=sys.stderr)

    # 3. medRxiv preprints
    print(f"\n🏥 Searching medRxiv preprints...", file=sys.stderr)
    medrxiv_articles = search_biorxiv(days=days, max_results=20, server="medrxiv")
    print(f"   Found {len(medrxiv_articles)} medRxiv preprints", file=sys.stderr)

    # 4. Clinical trials
    print(f"\n💊 Searching ClinicalTrials.gov...", file=sys.stderr)
    trials = search_clinical_trials(days=days, max_results=20)
    print(f"   Found {len(trials)} clinical trial updates", file=sys.stderr)

    # Combine articles
    all_articles = pubmed_articles + biorxiv_articles + medrxiv_articles

    # Deduplicate by DOI
    seen_dois = set()
    unique_articles = []
    for a in all_articles:
        doi = a.get("doi", "")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        unique_articles.append(a)

    # Compute stats
    stats = compute_stats(unique_articles, trials)

    print(f"\n✅ Total unique articles: {stats['total_articles']}", file=sys.stderr)
    print(f"   Sources: {json.dumps(stats['by_source'], indent=2)}", file=sys.stderr)
    print(f"   Categories: {json.dumps(stats['by_category'], indent=2)}", file=sys.stderr)

    # Output
    output = {
        "fetch_date": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "stats": stats,
        "articles": unique_articles,
        "clinical_trials": trials,
    }

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
