\# AI Job Search Agent



A multi-user, autonomous job search assistant that finds, evaluates, and helps you apply to relevant jobs faster — built end-to-end with a resume parser, LLM-based job matcher, auto-generated cover letters, interview prep, and approval-gated application auto-fill.



\*\*Live app:\*\* https://job-search-agent-7bkcyswjm8dgpkydbzcv3q.streamlit.app



\## Features



\- \*\*Resume parsing\*\* — upload a PDF/DOCX resume, automatically structured into skills, experience, education, and projects

\- \*\*Multi-source job search\*\* — pulls listings from RemoteOK, Arbeitnow, and OffCampusJobs4u

\- \*\*LLM-based matching\*\* — scores each job against your resume, highlighting matched and missing required skills

\- \*\*Cover letter generation\*\* — tailored per job, using only real details from your resume

\- \*\*Interview prep\*\* — generates likely HR and technical questions based on the role and your background

\- \*\*Follow-up reminders\*\* — flags applications with no response after 7 days and drafts a follow-up email

\- \*\*Application tracker\*\* — per-user, persistent dashboard of every job found, its status, and match score

\- \*\*Auto-fill (not auto-submit)\*\* — opens a real browser and fills in name/email/phone/resume for Greenhouse and Lever postings; a human always reviews and clicks Submit

\- \*\*Multi-user\*\* — each user signs up, uploads their own resume, and brings their own free Groq API key



\## Why no LinkedIn/Naukri/Indeed auto-apply?



These platforms explicitly prohibit automated applications in their Terms of Service, and automating them risks getting a user's own account banned. Jobs from these platforms can still be searched and displayed for manual application — this project only automates form-filling on platforms where it's safe and permitted (Greenhouse, Lever), and always leaves the final submit action to a human.



\## Tech stack



| Layer | Technology |

|---|---|

| Frontend / dashboard | \[Streamlit](https://streamlit.io/) |

| Auth | Firebase Authentication |

| Database | Firebase Firestore (per-user, isolated) |

| LLM inference | \[Groq](https://groq.com/) API (Llama 3.1 8B) |

| Resume parsing | `python-docx`, `pdfplumber` |

| Job scraping | `requests`, `BeautifulSoup4` |

| Browser automation | \[Playwright](https://playwright.dev/) |

| Hosting | Streamlit Community Cloud |



\## Architecture



User → Streamlit UI → Resume Parser → Job Search (RemoteOK / Arbeitnow / OffCampusJobs4u)

↓

JD Parser (LLM)

↓

Matcher (score + skill gap, LLM)

↓

Firestore Tracker (per-user) ← → Cover Letter / Interview Prep (LLM)

↓

Auto-fill Agent (Playwright, Greenhouse/Lever)



\## Project structure



job-agent/

├── app/

│ ├── resume\_parser.py # PDF/DOCX → structured JSON (LLM)

│ ├── jd\_parser.py # Raw job description → structured JSON (LLM)

│ ├── matcher.py # Resume vs JD → match score + skill gap (LLM)

│ ├── job\_search.py # Multi-source job fetching + filtering

│ ├── resume\_builder.py # Generates a tailored resume docx

│ ├── cover\_letter.py # Cover letter + follow-up email generation (LLM)

│ ├── interview\_prep.py # Interview question generation (LLM)

│ ├── apply\_agent.py # Playwright auto-fill (Greenhouse, Lever)

│ ├── tracker.py # Firestore-backed application tracker

│ └── auth.py # Firebase Auth + Firestore client setup

├── streamlit\_app.py # Main dashboard UI

└── requirements.txt



\## Running locally



```bash

git clone https://github.com/RoliMishra1819/job-search-agent.git

cd job-search-agent

python -m venv venv

venv\\Scripts\\activate          # Windows

pip install -r requirements.txt

playwright install chromium

```



Create a `.env` file in the project root:



GROQ\_API\_KEY=your\_groq\_key

FIREBASE\_API\_KEY=your\_firebase\_web\_api\_key

FIREBASE\_PROJECT\_ID=your\_firebase\_project\_id



Place your Firebase service account JSON at `firebase-service-account.json` in the project root.



Then run:



```bash

streamlit run streamlit\_app.py

```



\## Deployment



Deployed on Streamlit Community Cloud. Secrets (Firebase service account, API keys) are configured via Streamlit's secrets manager rather than `.env`, using a fallback pattern in `auth.py` and each LLM-calling module so the same codebase runs both locally and in the cloud.



\## Roadmap



\- \[ ] Workday auto-fill support

\- \[ ] Salary/compensation question handling (opt-in, user-defined answers only)

\- \[ ] Gmail integration for automatic follow-up detection



