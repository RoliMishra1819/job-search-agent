import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
import streamlit as st
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY")),
    max_retries=0,
)

JD_SCHEMA = {
    "job_title": "",
    "company": "",
    "location": "",
    "experience_required": "",     # e.g. "0-1 years", "fresher", "3+ years"
    "required_skills": [],
    "nice_to_have_skills": [],
    "responsibilities": [],
    "qualifications": []
}


def structure_jd(raw_text: str) -> dict:
    """Send raw job description text to the LLM and get back structured JSON."""
    prompt = f"""
You are a job description parser. Convert the following job description into JSON
matching exactly this schema (keep keys, fill values, use [] or "" if unknown):

{json.dumps(JD_SCHEMA, indent=2)}

IMPORTANT RULES:
- List every skill mentioned as required separately in "required_skills".
- Skills mentioned as "preferred", "nice to have", or "bonus" go in "nice_to_have_skills".
- If experience isn't stated explicitly but the role says "fresher", "graduate",
  "entry-level", or similar, set experience_required to "0-1 years".

Job description text:
\"\"\"
{raw_text}
\"\"\"

Return ONLY valid JSON. No markdown, no commentary.
"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=1200,
            )
        except Exception as e:
            if attempt == 2:
                raise ValueError(f"API call failed after 3 attempts: {e}")
            time.sleep(5)
            continue

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if attempt == 2:
                raise ValueError(f"LLM did not return valid JSON after 3 attempts:\n{content}")
            continue   


def parse_jd(raw_text: str) -> dict:
    """Entry point: raw JD text -> structured JSON."""
    if not raw_text.strip():
        raise ValueError("Empty job description text provided.")
    return structure_jd(raw_text)


if __name__ == "__main__":
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

    Qualifications:
    - Bachelor's degree in CS, Statistics, or related field
    """
    result = parse_jd(sample_jd)
    print(json.dumps(result, indent=2))