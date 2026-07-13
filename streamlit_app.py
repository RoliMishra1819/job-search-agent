import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from auth import sign_up, log_in, db
from tracker import get_all_jobs, get_stats, update_status, get_jobs_needing_followup, mark_followup_sent
from cover_letter import generate_cover_letter_text, generate_followup_email
from interview_prep import generate_interview_prep
from resume_parser import parse_resume
from firebase_admin import firestore
from apply_agent import autofill_greenhouse

st.set_page_config(page_title="Job Search Agent", layout="wide")

# --- Session state setup ---
if "user" not in st.session_state:
    st.session_state.user = None


def login_form():
    st.title("Job Search Agent")
    tab1, tab2 = st.tabs(["Log In", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In"):
            try:
                user = log_in(email, password)
                st.session_state.user = user
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            try:
                user = sign_up(new_email, new_password)
                st.session_state.user = user
                st.success("Account created!")
                st.rerun()
            except Exception as e:
                st.error(f"Signup failed: {e}")


def dashboard():
    user = st.session_state.user
    uid = user["localId"]

    st.sidebar.write(f"Logged in as: {user.get('email', 'unknown')}")
    if st.sidebar.button("Log Out"):
        st.session_state.user = None
        st.rerun()

    st.title("Job Search Agent Dashboard")

    st.subheader("Your Resume")

    doc = db.collection("users").document(uid).get()
    resume_data = doc.to_dict().get("resume_data") if doc.exists else None

    if resume_data:
        st.success(f"Resume on file: {resume_data.get('name', 'Uploaded')}")
        if st.button("Upload a different resume"):
            db.collection("users").document(uid).update({"resume_data": firestore.DELETE_FIELD})
            st.rerun()
    else:
        uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
        if uploaded_file is not None:
            temp_path = os.path.join("resumes", f"temp_{uid}{os.path.splitext(uploaded_file.name)[1]}")
            os.makedirs("resumes", exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Parsing your resume..."):
                try:
                    parsed = parse_resume(temp_path)
                    db.collection("users").document(uid).set({"resume_data": parsed}, merge=True)
                    st.success("Resume parsed and saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to parse resume: {e}")
                finally:
                    os.remove(temp_path)

    st.divider()

    st.subheader("Find Jobs")

    if not resume_data:
        st.warning("Upload a resume first before searching for jobs.")
    else:
        if st.button("Search for Matching Jobs"):
            with st.spinner("Searching and scoring jobs — this can take a few minutes..."):
                from job_search import fetch_remoteok_jobs, fetch_arbeitnow_jobs, filter_fresher_jobs, filter_relevant_titles
                from jd_parser import parse_jd
                from matcher import match_resume_to_jd
                from tracker import add_job
                import time as time_module

                search_terms = ["data analyst", "data scientist", "python developer", "machine learning"]
                remoteok_jobs, arbeitnow_jobs = [], []
                for term in search_terms:
                    remoteok_jobs += fetch_remoteok_jobs(keyword=term, limit=10)
                    arbeitnow_jobs += fetch_arbeitnow_jobs(keyword=term, limit=10)

                seen_urls = set()
                unique_jobs = []
                for job in remoteok_jobs + arbeitnow_jobs:
                    if job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        unique_jobs.append(job)

                candidates = filter_relevant_titles(filter_fresher_jobs(unique_jobs))

                found_count = 0
                for job in candidates:
                    description = job.get('description', '')[:800]
                    jd_text = f"{job['title']} at {job['company']}. {description}. Tags: {', '.join(job['tags'])}"
                    try:
                        jd_data = parse_jd(jd_text)
                        if not jd_data.get("required_skills"):
                            time_module.sleep(5)
                            continue
                        match_result = match_resume_to_jd(resume_data, jd_data)
                        score = match_result.get("match_score", 0)
                        if score >= 60:
                            add_job(uid, job['company'], job['title'], job['url'], score,
                                    missing_skills=match_result.get('missing_required', []))
                            found_count += 1
                        time_module.sleep(15)
                    except Exception:
                        time_module.sleep(5)
                        continue

                st.success(f"Search complete — {found_count} good matches added.")
                st.rerun()

    st.divider()

    stats = get_stats(uid)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Tracked", stats["total"])
    col2.metric("Saved", stats["saved"])
    col3.metric("Applied", stats["applied"])
    col4.metric("Interview", stats["interview"])
    col5.metric("Rejected", stats["rejected"])

    st.divider()

    followups_due = get_jobs_needing_followup(uid)
    if followups_due:
        st.subheader(f"Follow-ups Due ({len(followups_due)})")
        for job in followups_due:
            with st.container(border=True):
                st.write(f"**{job['role']}** @ {job['company']} — applied {job['date_applied']}, no response yet")
                if st.button("Generate Follow-up Email", key=f"gen_followup_{job['job_url']}"):
                    with st.spinner("Drafting..."):
                        email_text = generate_followup_email(resume_data, job)
                        st.session_state[f"followup_{job['job_url']}"] = email_text

                if f"followup_{job['job_url']}" in st.session_state:
                    st.text_area("Follow-up Email", st.session_state[f"followup_{job['job_url']}"], height=150, key=f"followup_display_{job['job_url']}")
                    col_a, col_b = st.columns(2)
                    col_a.download_button("Download as .txt", st.session_state[f"followup_{job['job_url']}"],
                                           file_name=f"Followup_{job['company']}.txt", key=f"dl_followup_{job['job_url']}")
                    if col_b.button("Mark as Sent", key=f"sent_{job['job_url']}"):
                        mark_followup_sent(uid, job["job_url"])
                        st.rerun()
        st.divider()

    jobs = get_all_jobs(uid)
    if not jobs:
        st.info("No jobs tracked yet.")
    else:
        for job in jobs:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                col1.write(f"**{job['role']}** @ {job['company']} — {job['match_score']}% match — *{job['status']}*")

                missing = job.get("missing_skills", [])
                if missing:
                    col1.caption(f"Missing skills: {', '.join(missing)}")
                else:
                    col1.caption("No missing required skills")

                if "greenhouse.io" in job.get("job_url", ""):
                    if col2.button("Auto-fill", key=f"fill_{job['job_url']}"):
                        st.info("Opening browser for auto-fill... check your taskbar for the Chromium window.")
                        from apply_agent import autofill_greenhouse
                        autofill_greenhouse(job["job_url"], resume_data, "resumes/master_resume.docx")

                if col3.button("Cover Letter", key=f"cl_{job['job_url']}"):
                    with st.spinner("Generating cover letter..."):
                        
                        jd_stub = {
                            "job_title": job["role"],
                            "company": job["company"],
                            "responsibilities": [],
                        }
                        match_stub = {
                            "matched_required": [],
                            "matched_nice_to_have": [],
                        }
                        letter_text = generate_cover_letter_text(resume_data, jd_stub, match_stub)
                        st.session_state[f"letter_{job['job_url']}"] = letter_text

                if f"letter_{job['job_url']}" in st.session_state:
                    st.text_area("Cover Letter", st.session_state[f"letter_{job['job_url']}"], height=200, key=f"letter_display_{job['job_url']}")
                    st.download_button("Download as .txt", st.session_state[f"letter_{job['job_url']}"],
                                        file_name=f"CoverLetter_{job['company']}.txt", key=f"dl_{job['job_url']}")

                if col4.button("Mark Applied", key=f"applied_{job['job_url']}"):
                    update_status(uid, job["job_url"], "Applied")
                    st.rerun()

                if col5.button("Interview Prep", key=f"prep_{job['job_url']}"):
                    with st.spinner("Generating prep sheet..."):
                        prep_text = generate_interview_prep(resume_data, job)
                        st.session_state[f"prep_{job['job_url']}_text"] = prep_text

                if f"prep_{job['job_url']}_text" in st.session_state:
                    st.text_area("Interview Prep", st.session_state[f"prep_{job['job_url']}_text"], height=300, key=f"prep_display_{job['job_url']}")
                    st.download_button("Download as .txt", st.session_state[f"prep_{job['job_url']}_text"],
                                        file_name=f"InterviewPrep_{job['company']}.txt", key=f"dl_prep_{job['job_url']}")

if st.session_state.user is None:
    login_form()
else:
    dashboard()