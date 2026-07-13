import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

from resume_parser import parse_resume
from jd_parser import parse_jd

load_dotenv()
import streamlit as st

try:
    groq_key = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
except Exception:
    groq_key = os.getenv("GROQ_API_KEY")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=groq_key,
)

def match_resume_to_jd(resume_json: dict, jd_json: dict) -> dict:
    """
    Compare a structured resume against a structured JD.
    Returns match score, matched/missing skills, and a recommendation.
    """
    resume_skills_text = "\n".join(resume_json.get("skills", []))
    jd_required = jd_json.get("required_skills", [])
    jd_nice_to_have = jd_json.get("nice_to_have_skills", [])

    prompt = f"""
You are a resume-to-job matcher. Compare the candidate's skills against
the job's required and nice-to-have skills.

Candidate skills (from resume, may be phrased as categories with sub-skills):
{resume_skills_text}

Job required skills:
{json.dumps(jd_required)}

Job nice-to-have skills:
{json.dumps(jd_nice_to_have)}

For EACH required skill, decide if the candidate has it based on the
candidate skills text (a skill counts as present if it's explicitly
mentioned or is a clear synonym/sub-skill of a listed category).

Return ONLY valid JSON in this exact shape:
{{
  "match_score": <integer 0-100, weighted mostly on required skills coverage>,
  "matched_required": [list of required skills the candidate has],
  "missing_required": [list of required skills the candidate lacks],
  "matched_nice_to_have": [list of nice-to-have skills the candidate has],
  "missing_nice_to_have": [list of nice-to-have skills the candidate lacks],
  "recommendation": "<one short sentence: apply, tailor resume first, or skip>"
}}
"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=700,
            )
        except Exception as e:
            if attempt == 2:
                raise ValueError(f"API call failed after 3 attempts: {e}")
            time.sleep(3)
            continue

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if attempt == 2:
                raise ValueError(f"LLM did not return valid JSON after 3 attempts:\n{content}")
            continue


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

    result = match_resume_to_jd(resume_data, jd_data)
    print(json.dumps(result, indent=2))