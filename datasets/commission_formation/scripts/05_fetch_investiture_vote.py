"""
05_fetch_investiture_vote.py
Fetch and parse the EP investiture vote from roll-call XML.
Enrich MEP records with country and party data from the EP Open Data API.

Output: investiture_vote.csv + .xlsx
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, fetch_url, save_both, normalize_name


def download_rcv_xml(logger) -> Path:
    """Download the EP roll-call vote XML for 27 Nov 2024."""
    xml_path = config.RAW_EP_XML / "PV-10-2024-11-27-RCV_EN.xml"
    if xml_path.exists():
        logger.info("RCV XML already downloaded.")
        return xml_path

    logger.info("Downloading EP roll-call vote XML...")
    resp = fetch_url(config.EP_RCV_XML_URL, timeout=60)
    xml_path.write_bytes(resp.content)
    logger.info(f"Saved XML ({len(resp.content):,} bytes)")
    return xml_path


def find_investiture_vote(xml_path: Path, logger) -> ET.Element:
    """
    Parse XML and find the Commission investiture vote.
    Look for RollCallVote.Result matching expected totals or description.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # The XML structure uses RollCallVote.Result elements
    # Try to find by description keyword first, then by vote totals
    candidates = []
    for vote_result in root.iter("RollCallVote.Result"):
        desc = vote_result.get("Description", "").lower()
        # Also check RollCallVote.Description.Text sub-element
        desc_elem = vote_result.find(".//RollCallVote.Description.Text")
        if desc_elem is not None and desc_elem.text:
            desc = desc_elem.text.lower()

        # Count votes
        result_for = vote_result.find(".//Result.For")
        result_against = vote_result.find(".//Result.Against")
        result_abstention = vote_result.find(".//Result.Abstention")

        n_for = int(result_for.get("Number", 0)) if result_for is not None else 0
        n_against = int(result_against.get("Number", 0)) if result_against is not None else 0
        n_abstain = int(result_abstention.get("Number", 0)) if result_abstention is not None else 0
        total = n_for + n_against + n_abstain

        candidates.append({
            "element": vote_result,
            "desc": desc,
            "for": n_for,
            "against": n_against,
            "abstain": n_abstain,
            "total": total,
        })

        logger.debug(f"Vote: for={n_for}, against={n_against}, abstain={n_abstain}, "
                      f"desc={desc[:80]}")

    # Strategy 1: Match by description keyword
    keyword = config.INVESTITURE_EXPECTED["description_keyword"]
    for c in candidates:
        if keyword in c["desc"]:
            logger.info(f"Found investiture vote by keyword '{keyword}': "
                        f"for={c['for']}, against={c['against']}, abstain={c['abstain']}")
            return c["element"]

    # Strategy 2: Match by expected totals
    exp = config.INVESTITURE_EXPECTED
    for c in candidates:
        if c["for"] == exp["for"] and c["against"] == exp["against"]:
            logger.info(f"Found investiture vote by expected totals: "
                        f"for={c['for']}, against={c['against']}, abstain={c['abstain']}")
            return c["element"]

    # Strategy 3: Find the vote with the most participants (investiture = big vote)
    if candidates:
        best = max(candidates, key=lambda c: c["total"])
        logger.warning(f"No exact match found. Using largest vote: "
                       f"for={best['for']}, against={best['against']}, "
                       f"abstain={best['abstain']}, total={best['total']}")
        return best["element"]

    raise ValueError("No RollCallVote.Result elements found in XML!")


def extract_mep_votes(vote_element: ET.Element, logger) -> List[Dict]:
    """Extract individual MEP votes from the vote element."""
    records = []

    vote_categories = [
        ("Result.For", "for", 1),
        ("Result.Against", "against", -1),
        ("Result.Abstention", "abstain", 0),
    ]

    for result_tag, vote_label, vote_numeric in vote_categories:
        result_elem = vote_element.find(f".//{result_tag}")
        if result_elem is None:
            continue

        for group in result_elem.findall(".//Result.PoliticalGroup.List"):
            group_id = group.get("Identifier", "")

            for mep in group.findall(".//PoliticalGroup.Member.Name"):
                mep_id = mep.get("MepId", "")
                pers_id = mep.get("PersId", "")
                full_name = mep.text.strip() if mep.text else ""

                records.append({
                    "mep_id": mep_id,
                    "pers_id": pers_id,
                    "full_name": full_name,
                    "ep_party_group": group_id,
                    "vote": vote_label,
                    "vote_numeric": vote_numeric,
                })

    logger.info(f"Extracted {len(records)} individual MEP votes")
    return records


def parse_mep_name(full_name: str) -> Tuple[str, str]:
    """
    Parse EP name format into (last_name, first_name).
    EP XML typically uses 'LAST FIRST' or 'LAST_NAME First_name' format.
    """
    if not full_name:
        return ("", "")

    # Handle common EP format: all-caps last name followed by first name
    parts = full_name.split()
    if not parts:
        return ("", "")

    # Find where uppercase part ends and mixed-case begins
    upper_parts = []
    first_parts = []
    found_first = False
    for p in parts:
        if not found_first and p == p.upper() and p.isalpha():
            upper_parts.append(p)
        else:
            found_first = True
            first_parts.append(p)

    if upper_parts and first_parts:
        last_name = " ".join(upper_parts).title()
        first_name = " ".join(first_parts)
    else:
        # Fallback: first word = first name, rest = last name
        first_name = parts[0]
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    return (last_name, first_name)


def fetch_mep_enrichment(logger) -> Dict:
    """
    Fetch MEP data from EP Open Data API for country enrichment.
    Uses PersId (= API identifier) for matching.

    The bulk list endpoint only returns name fields, so we fetch individual
    MEP records in batches to get country of representation.

    Returns dict keyed by PersId (API identifier) -> {country, country_name, ...}.
    """
    import time
    cache_dir = config.RAW_EP_XML / "api_cache"
    enrichment = {}

    try:
        logger.info("Fetching MEP data from EP Open Data API...")
        resp = fetch_url(config.EP_MEPS_API_URL, cache_dir=cache_dir, timeout=60)
        data = resp.json()

        # Save raw response
        raw_path = config.RAW_EP_XML / "meps_api_response.json"
        raw_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        members = data.get("data", [])
        logger.info(f"API returned {len(members)} MEPs for term 10")

        # Build basic identifier -> name mapping
        id_to_name = {}
        for member in members:
            if not isinstance(member, dict):
                continue
            identifier = str(member.get("identifier", ""))
            family_name = member.get("familyName", "")
            given_name = member.get("givenName", "")
            if identifier:
                id_to_name[identifier] = {
                    "family_name": family_name,
                    "given_name": given_name,
                }
                enrichment[identifier] = {
                    "country": "",
                    "country_name": "",
                    "national_party": "",
                    "given_name": given_name,
                    "family_name": family_name,
                }

        # Fetch individual MEP details to get country
        # Process in batches with rate limiting
        detail_cache = cache_dir / "mep_details"
        detail_cache.mkdir(parents=True, exist_ok=True)

        ids_to_fetch = list(id_to_name.keys())
        fetched = 0
        batch_size = 50
        logger.info(f"Fetching individual MEP details for country data ({len(ids_to_fetch)} MEPs)...")

        for i, pers_id in enumerate(ids_to_fetch):
            # Check cache first
            cache_file = detail_cache / f"{pers_id}.json"
            if cache_file.exists():
                try:
                    detail = json.loads(cache_file.read_text())
                except Exception:
                    detail = None
            else:
                # Fetch from API
                try:
                    detail_url = f"https://data.europarl.europa.eu/api/v2/meps/{pers_id}?format=application%2Fld%2Bjson"
                    detail_resp = fetch_url(detail_url, timeout=15, retries=2, backoff=1.0)
                    detail = detail_resp.json()
                    cache_file.write_text(json.dumps(detail, ensure_ascii=False))
                    fetched += 1

                    # Rate limit
                    if fetched % batch_size == 0:
                        logger.info(f"  Fetched {fetched}/{len(ids_to_fetch)} MEP details...")
                        time.sleep(1)

                except Exception:
                    detail = None

            if not detail:
                continue

            # Extract country from membership data
            mep_data = detail.get("data", [{}])
            if isinstance(mep_data, list) and mep_data:
                mep_data = mep_data[0]

            memberships = mep_data.get("hasMembership", [])
            if isinstance(memberships, dict):
                memberships = [memberships]

            country = ""
            for ms in memberships:
                if not isinstance(ms, dict):
                    continue
                # Country is in 'represents' field of MEMBER_PARLIAMENT role
                represents = ms.get("represents", [])
                if isinstance(represents, str):
                    represents = [represents]
                for rep in represents:
                    if "country/" in str(rep):
                        # Extract country code: ".../country/HUN" -> HUN
                        code_3 = rep.split("country/")[-1].upper()
                        # Convert 3-letter to 2-letter ISO
                        iso3_to_iso2 = {
                            "AUT": "AT", "BEL": "BE", "BGR": "BG", "CYP": "CY",
                            "CZE": "CZ", "DEU": "DE", "DNK": "DK", "EST": "EE",
                            "GRC": "EL", "ESP": "ES", "FIN": "FI", "FRA": "FR",
                            "HRV": "HR", "HUN": "HU", "IRL": "IE", "ITA": "IT",
                            "LTU": "LT", "LUX": "LU", "LVA": "LV", "MLT": "MT",
                            "NLD": "NL", "POL": "PL", "PRT": "PT", "ROU": "RO",
                            "SWE": "SE", "SVN": "SI", "SVK": "SK",
                        }
                        country = iso3_to_iso2.get(code_3, code_3[:2])
                        break
                if country:
                    break

            if country and pers_id in enrichment:
                enrichment[pers_id]["country"] = country
                enrichment[pers_id]["country_name"] = config.COUNTRY_NAMES.get(country, "")

        countries_found = sum(1 for v in enrichment.values() if v.get("country"))
        logger.info(f"Enrichment complete: {countries_found}/{len(enrichment)} MEPs have country data")

    except Exception as e:
        logger.warning(f"EP Open Data API fetch failed: {e}. "
                       f"Proceeding without enrichment.")

    return enrichment


def build_investiture_vote() -> pd.DataFrame:
    """Main function: download XML, parse vote, enrich MEPs, return DataFrame."""
    logger = setup_logging("05_investiture_vote")
    ensure_dirs()

    # Step 1: Download XML
    xml_path = download_rcv_xml(logger)

    # Step 2: Find the investiture vote
    vote_element = find_investiture_vote(xml_path, logger)

    # Step 3: Extract individual votes
    mep_votes = extract_mep_votes(vote_element, logger)

    # Step 4: Parse names
    for record in mep_votes:
        last_name, first_name = parse_mep_name(record["full_name"])
        record["last_name"] = last_name
        record["first_name"] = first_name

    # Step 5: Enrich with country/party data (match by PersId = API identifier)
    enrichment = fetch_mep_enrichment(logger)
    matched = 0
    for record in mep_votes:
        pers_id = record.get("pers_id", "")
        mep_data = enrichment.get(pers_id, {})

        record["country"] = mep_data.get("country", "")
        record["country_name"] = mep_data.get("country_name", "")
        record["national_party"] = mep_data.get("national_party", "")

        # Use API name data to get proper first/last names if available
        if mep_data.get("given_name"):
            record["first_name"] = mep_data["given_name"]
        if mep_data.get("family_name"):
            record["last_name"] = mep_data["family_name"]

        if record["country"]:
            matched += 1

    logger.info(f"PersId-based enrichment matched {matched}/{len(mep_votes)} MEPs with country")

    # Map EP party group short codes to full names
    for record in mep_votes:
        record["ep_party_group_full"] = config.EP_PARTY_GROUP_NAMES.get(
            record["ep_party_group"], record["ep_party_group"]
        )

    # Step 6: Add vote date
    for record in mep_votes:
        record["vote_date"] = config.INVESTITURE_EXPECTED["date"]

    # Create DataFrame with proper column order
    df = pd.DataFrame(mep_votes)
    columns = [
        "mep_id", "full_name", "last_name", "first_name",
        "country", "country_name", "ep_party_group", "ep_party_group_full",
        "national_party", "vote", "vote_numeric", "vote_date",
    ]
    # Only include columns that exist
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    # Sort by party group then name
    df = df.sort_values(["ep_party_group", "last_name"]).reset_index(drop=True)

    # Validation
    vote_counts = df["vote"].value_counts()
    logger.info(f"Vote totals: {vote_counts.to_dict()}")

    exp = config.INVESTITURE_EXPECTED
    if vote_counts.get("for", 0) == exp["for"]:
        logger.info("Vote-for count matches expected total.")
    else:
        logger.warning(
            f"Vote-for count {vote_counts.get('for', 0)} != expected {exp['for']}"
        )

    return df


def main():
    df = build_investiture_vote()
    save_both(df, "investiture_vote")
    print(f"investiture_vote: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
