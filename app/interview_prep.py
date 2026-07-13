import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
import streamlit as st
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY")),
    max_retries=0,
)

def generate_interview_prep(resume_json: dict, job: dict) -> str:
    """
    Generate likely interview questions for a specific job, tailored to the
    candidate's actual background so prep is relevant, not generic.
    """
    skills_text = "\n".join(resume_json.get("skills", []))
    projects_text = ", ".join(p.get("name", "") for p in resume_json.get("projects", []))

    prompt = f"""
You are helping a candidate prepare for a job interview. Generate a focused prep sheet.

Candidate background:
- Skills: {skills_text}
- Projects: {projects_text}
- Summary: {resume_json.get('summary', '')}

Job: {job.get('role', '')} at {job.get('company', '')}

Generate:
1. 5 likely HR/behavioral questions (specific to this role, not generic "tell me about yourself" filler)
2. 5 likely technical questions based on the skills required for this role
3. 3 questions the candidate should ask the interviewer

Format as plain text with clear section headers. No markdown symbols like ** or #.
Keep it concise and actionable.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=900,
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    from resume_parser import parse_resume

    resume_data = parse_resume("resumes/master_resume.docx")
    test_job = {"role": "Data Analyst", "company": "Example Corp"}

    result = generate_interview_prep(resume_data, test_job)
    print(result)