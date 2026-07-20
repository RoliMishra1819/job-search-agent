from playwright.sync_api import sync_playwright
import time


def autofill_greenhouse(job_url: str, resume_json: dict, resume_file_path: str, cover_letter_path: str = None):
    """
    Opens a Greenhouse job application page and auto-fills common fields.
    Leaves the browser open for the user to review and submit manually.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible browser so user can review
        page = browser.new_page()
        page.goto(job_url, timeout=30000)
        page.wait_for_load_state("networkidle")

        name_parts = resume_json.get("name", "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        filled_fields = []

        # Common Greenhouse field selectors (id-based, fairly stable across companies)
        field_map = {
            "#first_name": first_name,
            "#last_name": last_name,
            "#email": resume_json.get("email", ""),
            "#phone": resume_json.get("phone", ""),
            "#job_application_answers_attributes_0_text_value": resume_json.get("linkedin", ""),  # LinkedIn (common Greenhouse pattern, may vary)
        }

        for selector, value in field_map.items():
            if value:
                try:
                    if page.locator(selector).count() > 0:
                        page.fill(selector, value)
                        filled_fields.append(selector)
                except Exception:
                    pass  # field might not exist on this particular posting, skip silently

        # Resume upload (Greenhouse typically uses a file input with id="resume")
        try:
            if page.locator("#resume").count() > 0:
                page.set_input_files("#resume", resume_file_path)
                filled_fields.append("#resume (file)")
        except Exception:
            pass

        # Cover letter upload, if the field exists and we have one
        if cover_letter_path:
            try:
                if page.locator("#cover_letter").count() > 0:
                    page.set_input_files("#cover_letter", cover_letter_path)
                    filled_fields.append("#cover_letter (file)")
            except Exception:
                pass

        print(f"Auto-filled fields: {filled_fields}")
        print("Browser left open for review. Custom questions (experience, salary, work authorization, etc.)")
        print("need your manual input — these are personal/legal answers that shouldn't be auto-generated.")
        print("Please check the form, fill remaining fields, then submit manually.")

        browser.close()


def autofill_lever(job_url: str, resume_json: dict, resume_file_path: str, cover_letter_path: str = None):
    """
    Opens a Lever job application page and auto-fills common fields.
    Leaves the browser open for the user to review and submit manually.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(job_url, timeout=30000)
        page.wait_for_load_state("networkidle")

        filled_fields = []

        # Lever's common field selectors (name-based, fairly stable across companies)
        field_map = {
            'input[name="name"]': resume_json.get("name", ""),
            'input[name="email"]': resume_json.get("email", ""),
            'input[name="phone"]': resume_json.get("phone", ""),
            'input[name="urls[LinkedIn]"]': resume_json.get("linkedin", ""),
            'input[name="urls[GitHub]"]': resume_json.get("github", ""),
        }

        for selector, value in field_map.items():
            if value:
                try:
                    if page.locator(selector).count() > 0:
                        page.fill(selector, value)
                        filled_fields.append(selector)
                except Exception:
                    pass

        # Resume upload (Lever typically uses name="resume")
        try:
            if page.locator('input[name="resume"]').count() > 0:
                page.set_input_files('input[name="resume"]', resume_file_path)
                filled_fields.append("resume (file)")
        except Exception:
            pass

        print(f"Auto-filled fields: {filled_fields}")
        print("Browser left open for review. Custom questions need your manual input.")
        print("Please check the form, fill remaining fields, then submit manually.")
        input("Press Enter here to close the browser when done...")

        browser.close()


if __name__ == "__main__":
    test_resume = {
        "name": "Roli Mishra",
        "email": "roli85756@gmail.com",
        "phone": "8869944959",
        "linkedin": "www.linkedin.com/in/roli-mishra",
    }
    platform = input("Test which platform? (greenhouse/lever): ").strip().lower()
    test_url = input("Paste the job application URL: ")
    if platform == "greenhouse":
        autofill_greenhouse(test_url, test_resume, "resumes/master_resume.docx")
    elif platform == "lever":
        autofill_lever(test_url, test_resume, "resumes/master_resume.docx")
    else:
        print("Unknown platform")