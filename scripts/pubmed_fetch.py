#!/usr/bin/env python3
"""Fetch recent mRNA therapeutics publications from PubMed via E-utilities."""

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

QUERY = (
    '("mRNA therapeutics" OR "mRNA vaccine" OR "mRNA-based" '
    'OR "lipid nanoparticle" OR "LNP delivery" OR "modified mRNA" '
    'OR "self-amplifying RNA" OR "saRNA" OR "nucleoside-modified mRNA" '
    'OR "mRNA therapy" OR "mRNA lipid nanoparticle")'
)


def esearch(query: str, days: int = 7, max_results: int = 40) -> list[str]:
    """Search PubMed, return list of PMIDs."""
    today = datetime.now(timezone.utc)
    mindate = (today - timedelta(days=days)).strftime("%Y/%m/%d")
    maxdate = today.strftime("%Y/%m/%d")
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "relevance",
        "datetype": "pdat",
        "mindate": mindate,
        "maxdate": maxdate,
        "retmode": "json",
    })
    url = f"{BASE}/esearch.fcgi?{params}"
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    return data.get("esearchresult", {}).get("idlist", [])


def efetch(pmids: list[str]) -> list[dict]:
    """Fetch article details for given PMIDs."""
    if not pmids:
        return []
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    })
    url = f"{BASE}/efetch.fcgi?{params}"
    with urllib.request.urlopen(url, timeout=60) as r:
        xml_data = r.read().decode("utf-8")

    articles = []
    for article_xml in xml_data.split("<PubmedArticle>")[1:]:
        def extract(tag):
            start = article_xml.find(f"<{tag}>")
            end = article_xml.find(f"</{tag}>")
            if start == -1 or end == -1:
                return ""
            return article_xml[start + len(tag) + 2:end].strip()

        def extract_abstract():
            start = article_xml.find("<Abstract>")
            end = article_xml.find("</Abstract>")
            if start == -1 or end == -1:
                return ""
            block = article_xml[start:end]
            parts = []
            for seg in block.split("<AbstractText")[1:]:
                close = seg.find("</AbstractText>")
                if close == -1:
                    continue
                # Extract label if present
                label_start = seg.find('Label="')
                label = ""
                if label_start != -1 and label_start < seg.find(">"):
                    label_end = seg.find('"', label_start + 7)
                    label = seg[label_start + 7:label_end]
                text = seg[seg.find(">") + 1:close]
                if label:
                    parts.append(f"**{label}:** {text.strip()}")
                else:
                    parts.append(text.strip())
            return " ".join(parts)

        pmid = extract("PMID")
        title = extract("ArticleTitle")
        abstract = extract_abstract()
        journal = extract("Title")
        year = extract("Year")
        month = extract("Month")
        day = extract("Day")

        # DOI
        doi = ""
        doi_start = article_xml.find('EIdType="doi"')
        if doi_start != -1:
            doi_seg = article_xml[doi_start:]
            ds = doi_seg.find(">")
            de = doi_seg.find("</ArticleId>")
            if ds != -1 and de != -1:
                doi = doi_seg[ds + 1:de].strip()

        # Authors
        authors = []
        for auth in article_xml.split("<Author")[1:]:
            ln, fn = "", ""
            ls, le = auth.find("<LastName>"), auth.find("</LastName>")
            fs, fe = auth.find("<ForeName>"), auth.find("</ForeName>")
            if ls != -1 and le != -1:
                ln = auth[ls + 10:le]
            if fs != -1 and fe != -1:
                fn = auth[fs + 10:fe]
            if ln:
                authors.append(f"{ln} {fn}".strip())

        articles.append({
            "pmid": pmid,
            "title": title,
            "authors": authors[:6],
            "journal": journal,
            "date": f"{year}-{month}-{day}",
            "doi": doi,
            "abstract": abstract,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return articles


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    print(f"Searching PubMed for mRNA therapeutics (last {days} days)...", file=sys.stderr)
    pmids = esearch(QUERY, days=days, max_results=max_results)
    print(f"Found {len(pmids)} articles.", file=sys.stderr)
    articles = efetch(pmids)
    json.dump(articles, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
