from datetime import datetime
from auth import db


def add_job(uid: str, company: str, role: str, job_url: str, match_score: int,
            missing_skills: list = None, job_title_raw: str = "",
            resume_path: str = "", cover_letter_path: str = "") -> bool:
    """Insert a job into this user's tracked applications. Returns False if it already exists (by URL)."""
    doc_id = job_url.replace("/", "_").replace(":", "_")  # Firestore doc IDs can't contain slashes
    doc_ref = db.collection("users").document(uid).collection("applications").document(doc_id)

    if doc_ref.get().exists:
        return False

    doc_ref.set({
        "company": company,
        "role": role,
        "job_url": job_url,
        "match_score": match_score,
        "missing_skills": missing_skills or [],
        "status": "Saved",
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "date_found": datetime.now().strftime("%Y-%m-%d"),
        "date_applied": None,
    })
    return True

def update_status(uid: str, job_url: str, status: str):
    """Update a job's status for this user, e.g. 'Applied', 'Interview', 'Rejected'."""
    doc_id = job_url.replace("/", "_").replace(":", "_")
    doc_ref = db.collection("users").document(uid).collection("applications").document(doc_id)

    update_data = {"status": status}
    if status == "Applied":
        update_data["date_applied"] = datetime.now().strftime("%Y-%m-%d")

    doc_ref.update(update_data)


def get_all_jobs(uid: str) -> list:
    """Return all tracked jobs for this user as a list of dicts."""
    docs = db.collection("users").document(uid).collection("applications").stream()
    jobs = [doc.to_dict() for doc in docs]
    jobs.sort(key=lambda j: j.get("date_found", ""), reverse=True)
    return jobs


def get_stats(uid: str) -> dict:
    """Summary counts for this user's dashboard."""
    jobs = get_all_jobs(uid)
    return {
        "total": len(jobs),
        "saved": sum(1 for j in jobs if j["status"] == "Saved"),
        "applied": sum(1 for j in jobs if j["status"] == "Applied"),
        "interview": sum(1 for j in jobs if j["status"] == "Interview"),
        "rejected": sum(1 for j in jobs if j["status"] == "Rejected"),
    }

def get_jobs_needing_followup(uid: str, days_threshold: int = 7) -> list:
    """
    Return jobs that were marked Applied more than `days_threshold` days ago
    and haven't had a follow-up sent yet.
    """
    from datetime import datetime, timedelta

    jobs = get_all_jobs(uid)
    cutoff = datetime.now() - timedelta(days=days_threshold)

    due = []
    for job in jobs:
        if job.get("status") != "Applied":
            continue
        if job.get("followup_sent"):
            continue
        date_applied = job.get("date_applied")
        if not date_applied:
            continue
        try:
            applied_dt = datetime.strptime(date_applied, "%Y-%m-%d")
        except ValueError:
            continue
        if applied_dt <= cutoff:
            due.append(job)

    return due


def mark_followup_sent(uid: str, job_url: str):
    """Mark a job's follow-up as sent so it doesn't show up again."""
    doc_id = job_url.replace("/", "_").replace(":", "_")
    doc_ref = db.collection("users").document(uid).collection("applications").document(doc_id)
    doc_ref.update({"followup_sent": True})


if __name__ == "__main__":
    test_uid = "test_uid_123"
    added = add_job(test_uid, "Test Company", "Test Role", "https://example.com/job/1", 75)
    print("Added:" if added else "Already exists:", "Test Role")

    print("\nAll tracked jobs for test user:")
    for job in get_all_jobs(test_uid):
        print(job)

    print("\nStats:", get_stats(test_uid))