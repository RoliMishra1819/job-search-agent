import os
import re
from docx import Document
from docx.shared import Pt
from openai import OpenAI
from dotenv import load_dotenv

from resume_parser import parse_resume
from jd_parser import parse_jd
from matcher import match_resume_to_jd

load_dotenv()
import streamlit as st

try:
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
except Exception:
    groq_key = os.getenv("GROQ_API_KEY")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=groq_key,
    max_retries=0,
)
def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\s-]", "", name).strip()
    return re.sub(r"[\s]+", "_", name)


def generate_cover_letter_text(resume_json: dict, jd_json: dict, match_result: dict) -> str:
    """Use the LLM to draft a tailored, truthful cover letter."""
    matched_skills = match_result.get("matched_required", []) + match_result.get("matched_nice_to_have", [])

    prompt = f"""
Write a professional cover letter for a job application. Be concise (250-350 words),
genuine, and specific — no generic filler phrases like "team player" or "hard worker"
without evidence.

Candidate name: {resume_json.get('name', '')}
Candidate summary: {resume_json.get('summary', '')}
Candidate's relevant matched skills for this role: {', '.join(matched_skills)}
Candidate's projects: {[p.get('name') for p in resume_json.get('projects', [])]}

Job title: {jd_json.get('job_title', '')}
Company: {jd_json.get('company', '')}
Key responsibilities: {', '.join(jd_json.get('responsibilities', []))}

Rules:
- Only reference skills/projects/experience actually listed above. Do not invent anything.
- Address it "Dear Hiring Manager," unless a specific name is given.
- End with a professional sign-off using the candidate's name.
- Return ONLY the letter body text, no subject line, no markdown.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=600,
    )

    return response.choices[0].message.content.strip()


def build_cover_letter_docx(letter_text: str, company_name: str, output_dir: str = "cover_letters") -> str:
    os.makedirs(output_dir, exist_ok=True)

    doc = Document()
    for paragraph in letter_text.split("\n\n"):
        p = doc.add_paragraph(paragraph.strip())
        p.paragraph_format.space_after = Pt(10)

    filename = f"CoverLetter_{sanitize_filename(company_name)}.docx"
    output_path = os.path.join(output_dir, filename)
    doc.save(output_path)
    return output_path

def generate_followup_email(resume_json: dict, job: dict) -> str:
    """Generate a short, polite follow-up email for an application with no response."""
    prompt = f"""
Write a brief, professional follow-up email for a job application with no response yet.
Keep it under 120 words. Polite, not pushy. Reaffirm interest, ask about status.

Candidate name: {resume_json.get('name', '')}
Job title: {job.get('role', '')}
Company: {job.get('company', '')}
Date applied: {job.get('date_applied', '')}

Return ONLY the email body text, no subject line, no markdown.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    resume_data = parse_resume("resumes/master_resume.docx")

    sample_jd = """
    Data Analyst - Fresher
    Company: Example Corp
    Location: Bangalore, India

    We are looking for a fresher Data Analyst with strong skills in:
    - Python
    - SQL
    - Power BI
    - Excel
    - Tableau
    - Statistics

    Nice to have: AWS, Azure

    Responsibilities:
    - Analyze large datasets
    - Build dashboards
    - Present insights to stakeholders
    """
    jd_data = parse_jd(sample_jd)
    match_result = match_resume_to_jd(resume_data, jd_data)

    letter_text = generate_cover_letter_text(resume_data, jd_data, match_result)
    path = build_cover_letter_docx(letter_text, jd_data.get("company", "UnknownCompany"))
    print(f"Cover letter saved to: {path}")
    print("\n--- Preview ---\n")
    print(letter_text)