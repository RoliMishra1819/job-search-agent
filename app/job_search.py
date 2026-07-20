import time
import requests
from bs4 import BeautifulSoup

REMOTEOK_API = "https://remoteok.com/api"


def fetch_remoteok_jobs(keyword: str = "", limit: int = 20) -> list:
    """
    Fetch jobs from RemoteOK's public API.
    Optionally filter by a keyword appearing in the job title or tags.
    """
    headers = {"User-Agent": "Mozilla/5.0 (job-search-agent)"}
    response = requests.get(REMOTEOK_API, headers=headers, timeout=15)
    
    response.raise_for_status()

    data = response.json()
    
    # First element is usually a metadata/legal blob, skip it
    jobs = [item for item in data if isinstance(item, dict) and item.get("id")]

    if keyword:
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        jobs = [
            job for job in jobs
            if keyword_lower in job.get("position", "").lower()
            or any(word in tag.lower() for tag in job.get("tags", []) for word in keyword_words)
        ]

    results = []
    for job in jobs[:limit]:
        results.append({
            "title": job.get("position", ""),
            "company": job.get("company", ""),
            "location": job.get("location", "Remote"),
            "tags": job.get("tags", []),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "date_posted": job.get("date", ""),
        })

    return results

ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"


def fetch_arbeitnow_jobs(keyword: str = "", limit: int = 20) -> list:
    """Fetch jobs from Arbeitnow's free public API (tech-focused)."""
    response = requests.get(ARBEITNOW_API, timeout=15)
    response.raise_for_status()

    data = response.json().get("data", [])

    if keyword:
        keyword_lower = keyword.lower()
        keyword_words = keyword_lower.split()
        data = [
            job for job in data
            if keyword_lower in job.get("title", "").lower()
            or any(word in tag.lower() for tag in job.get("tags", []) for word in keyword_words)
        ]

    results = []
    for job in data[:limit]:
        results.append({
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": job.get("location", "Remote"),
            "tags": job.get("tags", []),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "date_posted": str(job.get("created_at", "")),
        })

    return results

def fetch_offcampusjobs4u_jobs(limit: int = 20) -> list:
    """
    Scrape OffCampusJobs4u.com's homepage listing for fresher job posts.
    Returns title + link to the article (which contains the real apply link).
    """
    headers = {"User-Agent": "Mozilla/5.0 (job-search-agent)"}
    response = requests.get("https://offcampusjobs4u.com/", headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen_urls = set()

    for h3 in soup.find_all("h3"):
        link = h3.find("a")
        if not link or not link.get("href"):
            continue
        url = link["href"]
        title = link.get_text(strip=True)
        if url in seen_urls or not title:
            continue
        seen_urls.add(url)

        results.append({
            "title": title,
            "company": "",  # unknown until parsed from title/article — filled in by jd_parser later
            "location": "",
            "tags": [],
            "url": url,
            "description": title,  # title itself has most of the signal (Company | Role | Location)
            "date_posted": "",
        })
        if len(results) >= limit:
            break

    return results


def fetch_offcampusjobs4u_article_details(article_url: str) -> dict:
    """
    Fetch a single OffCampusJobs4u article and extract:
    - full text content (for skill/requirement matching)
    - the real external "Apply" link (not the article page itself)
    """
    headers = {"User-Agent": "Mozilla/5.0 (job-search-agent)"}
    response = requests.get(article_url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    article = soup.find("article") or soup.find("div", class_="entry-content") or soup
    paragraphs = article.find_all(["p", "li", "td"])
    content_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    apply_url = article_url  # fallback: link to the article itself
    for link in article.find_all("a", href=True):
        link_text = link.get_text(strip=True).lower()
        href = link["href"]
        is_external_http = href.startswith("http") and "offcampusjobs4u.com" not in href
        if is_external_http and "apply" in link_text:
            apply_url = href
            break  # first match — real apply link appears before footer promo links

    return {
        "content": content_text[:3000],  # cap length for token budget
        "apply_url": apply_url,
    }



def filter_fresher_jobs(jobs: list) -> list:
    """
    Drop jobs whose title/tags suggest senior-level requirements.
    Simple heuristic filter — refine later based on real data.
    """
    exclude_terms = ["senior", "sr.", "lead", "staff", "principal", "5+ years", "manager"]
    filtered = []
    for job in jobs:
        title_lower = job.get("title", "").lower()
        if any(term in title_lower for term in exclude_terms):
            continue
        filtered.append(job)
    return filtered

def filter_relevant_titles(jobs: list, role_keywords: list = None) -> list:
    """
    Keep only jobs whose title matches your target role keywords.
    Prevents wasting API calls scoring clearly unrelated roles.
    """
    if role_keywords is None:
        role_keywords = [
            "data analyst", "data scientist", "data science", "machine learning",
            "ml engineer", "ai engineer", "python developer", "software engineer",
            "software developer", "backend developer", "full stack", "data engineer",
            "analytics", "graduate engineer trainee", "sde"
        ]
    filtered = []
    for job in jobs:
        title_lower = job.get("title", "").lower()
        if any(kw in title_lower for kw in role_keywords):
            filtered.append(job)
    return filtered


if __name__ == "__main__":
    from resume_parser import parse_resume
    from jd_parser import parse_jd
    from matcher import match_resume_to_jd
    from tracker import add_job

    resume_data = parse_resume("resumes/master_resume.docx")

    search_terms = ["data analyst", "data scientist", "python developer", "machine learning"]

    remoteok_jobs = []
    arbeitnow_jobs = []
    for term in search_terms:
        r = fetch_remoteok_jobs(keyword=term, limit=10)
        a = fetch_arbeitnow_jobs(keyword=term, limit=10)
        
        remoteok_jobs += r
        arbeitnow_jobs += a

    offcampus_jobs = fetch_offcampusjobs4u_jobs(limit=30)

    # de-dupe by URL in case multiple keywords/sources caught the same job
    seen_urls = set()
    unique_jobs = []
    for job in remoteok_jobs + arbeitnow_jobs + offcampus_jobs:
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            unique_jobs.append(job)
    combined = unique_jobs
    

    all_jobs = filter_fresher_jobs(combined)
    

    all_jobs = filter_relevant_titles(all_jobs)
    

    print(f"Fetched {len(all_jobs)} candidate jobs. Scoring against your resume...\n")

    good_matches = []
    for job in all_jobs:
        # For OffCampusJobs4u listings, fetch the full article for real skill/requirement content and the real apply link
        if "offcampusjobs4u.com" in job.get("url", ""):
            try:
                details = fetch_offcampusjobs4u_article_details(job["url"])
                job["description"] = details["content"]
                job["url"] = details["apply_url"]  # point to the real external application, not our article link
            except Exception:
                pass  # fall back to title-only if the article fetch fails

        description = job.get('description', '')[:800]
        jd_text = f"{job['title']} at {job['company']}. {description}. Tags: {', '.join(job['tags'])}"
        try:
            jd_data = parse_jd(jd_text)
            if not jd_data.get("required_skills"):
                print(f"Skipped '{job['title']}' — no concrete required skills extracted\n")
                time.sleep(5)
                continue
            match_result = match_resume_to_jd(resume_data, jd_data)
            score = match_result.get("match_score", 0)
            if score >= 60:
                good_matches.append((score, job, match_result))
            time.sleep(15)
        except Exception as e:
            print(f"Skipped '{job['title']}' due to error: {e}")
            time.sleep(2)
            continue

    good_matches.sort(key=lambda x: x[0], reverse=True)

    test_uid = "test_uid_123"  # placeholder for CLI testing — real UI will use the logged-in user's uid
    print(f"\n{len(good_matches)} good matches (score >= 60):\n")
    for score, job, match_result in good_matches:
        print(f"[{score}%] {job['title']} @ {job['company']} — {job['url']}")
        print(f"   Missing: {match_result.get('missing_required', [])}\n")
        added = add_job(test_uid, job['company'], job['title'], job['url'], score)