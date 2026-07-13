import time
import requests

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

    # de-dupe by URL in case multiple keywords caught the same job
    seen_urls = set()
    unique_jobs = []
    for job in remoteok_jobs + arbeitnow_jobs:
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            unique_jobs.append(job)
    remoteok_jobs, arbeitnow_jobs = unique_jobs, []
    combined = remoteok_jobs + arbeitnow_jobs
    

    all_jobs = filter_fresher_jobs(combined)
    

    all_jobs = filter_relevant_titles(all_jobs)
    

    print(f"Fetched {len(all_jobs)} candidate jobs. Scoring against your resume...\n")

    good_matches = []
    for job in all_jobs:
        description = job.get('description', '')[:800]  # cap length to control token usage
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