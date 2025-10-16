import os
import requests
import json, re
import base64
import google.generativeai as genai
from fastapi import FastAPI


# ==============================================================
# 1. CONFIGURATION
# ==============================================================
app = FastAPI()
# --- Load environment variables ---
GITHUB_SECRET = os.getenv("GITHUB_SECRET")
if not GITHUB_SECRET:
    raise ValueError("Please set the GITHUB_SECRET environment variable")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)

# --- GitHub API base URL ---
API_URL = "https://api.github.com"

# --- Payload (project brief and metadata) ---
'''
payload = {
    "email": "student@example.com",
    "secret": "a46mnl09p7n9",
    "task": "Fib",
    "round": 1,
    "nonce": "125ab",
    "brief": "Create a program that prints the first 10 Fibonacci numbers",
    "checks": [
        "Repo has MIT license",
        "README.md is professional",
        "Page displays captcha URL passed at ?url=...",
        "Page displays solved captcha text within 15 seconds",
    ],
    "evaluation_url": "https://example.com/notify",
    "attachments": [{"name": "sample.png", "url": "data:image/png;base64,iVBORw..."}],
}
'''
# --- Default index.html content ---
index_html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Captcha Solver</title>
</head>
<body>
    <h1>Captcha Solver</h1>
    <p id="captcha-url">Loading captcha...</p>
    <p id="captcha-solution">Solving captcha...</p>
    <script>
        async function fetchCaptcha() {
            const urlParams = new URLSearchParams(window.location.search);
            const captchaUrl = urlParams.get('url');
            document.getElementById('captcha-url').innerText = `Captcha URL: ${captchaUrl}`;
            if (captchaUrl) {
                try {
                    const response = await fetch(captchaUrl);
                    const text = await response.text();
                    document.getElementById('captcha-solution').innerText = `Captcha Solution: ${text}`;
                } catch (error) {
                    document.getElementById('captcha-solution').innerText = 'Error fetching captcha.';
                }
            } else {
                document.getElementById('captcha-solution').innerText = 'No captcha URL provided.';
            }
        }
        window.onload = fetchCaptcha;
    </script>
</body>
</html>"""

# ==============================================================
# 2. GEMINI: GENERATE APP CODE FROM BRIEF
# ==============================================================

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No valid JSON found")


def generate_app_from_brief(brief):
    """
    Sends the project brief to Gemini and gets back generated code.
    Expects the model to return JSON: {"files": {"filename": "content", ...}}
    """
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = f"""
    You are an expert full-stack developer.
    Build a minimal, working application according to the following brief:
    ---
    {brief}
    ---

    Return ONLY valid JSON with this structure excluding extra non-JSON characters: the backticks and the json\n preamble, as well as potential invisible characters (like a non-breaking space) that might be present in the original input, specifically the spaces used for indentation.

:
    {{
      "files": {{
        "main.py": "<code here>",
        "README.md": '<complete markdown readme with sections: Summary, Setup, Usage, Code Explanation, License>',
        "index.html": "<complete html code with interactive form: title, input field, submit button, JS to handle form and display results>",

      }}
    }}
    Do not include explanations or markdown formatting.
    """

    print("🤖 Sending brief to Gemini...")
    response = model.generate_content(prompt)

    try:
        json_text = response.text.strip()
        if json_text.startswith('```json'):
            json_text = json_text.lstrip('`json\n').rstrip('`')
    
            # 2. IMPORTANT: Replace the non-breaking space character (U+00A0) 
            # which is often copied with text and is invalid in standard JSON 
            # for indentation or as a regular space.
            # The character ' ' in your text is likely U+00A0.
            # We replace it with a standard space ' '.
            json_text = json_text.replace('\xa0', ' ')
        app_json = json.loads(json_text)
        files = app_json.get("files", {})
        print(f"✅ Gemini generated {len(files)} file(s).")
        return files
    except Exception as e:
        print("⚠️ Error parsing Gemini output:", e)
        print("Raw response:\n", response.text)
        return {"main.py": "# Gemini output error\nprint('Hello World')"}

# ==============================================================
# 3. GITHUB AUTOMATION FUNCTIONS
# ==============================================================

def create_repo(payload):
    """Creates a new GitHub repository."""
    repo_name = payload["task"].lower()
    repo_description = payload["brief"]

    url = f"{API_URL}/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "name": repo_name,
        # "auto_init": True,
        "description": repo_description,
        "private": False,
        "license_template": "mit",
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        full_name = response.json()["full_name"]
        print(f"✅ Repository '{full_name}' created successfully.")
        return response.json()
    else:
        print(f"❌ Error creating repository: {response.content}")
        return None


def create_file(repo_full_name, file_path, content):
    """Creates or updates a file in the repository."""
    url = f"{API_URL}/repos/{repo_full_name}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }
    encoded_content = base64.b64encode(content.encode()).decode()
    data = {
        "message": f"Add {file_path}",
        "content": encoded_content,
        "branch": "main",
    }

    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"📄 File '{file_path}' created successfully.")
    else:
        print(f"⚠️ Error creating file '{file_path}': {response.content}")


def enable_pages(repo_full_name):
    """Enables GitHub Pages for a repository."""
    url = f"{API_URL}/repos/{repo_full_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"source": {"branch": "main", "path": "/"}}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code in (201, 204):
        print("🌐 GitHub Pages enabled successfully.")
    else:
        print(f"⚠️ Error enabling GitHub Pages: {response.content}")

# ==============================================================
# 4. MAIN PIPELINE
# ==============================================================
def validate_secret(secret: str) -> bool:
    print(os.getenv("SECRET"))
    return secret == os.getenv("SECRET")

@app.post("/handle_task")
async def handle_task(payload: dict):
    print("🚀 Starting Auto App Builder...\n")
    if not validate_secret(payload.get("secret", "")):
        return {"error": "Invalid secret"}
    else:
        if payload.get("round") == 1:
            repo_info = create_repo(payload)
            if repo_info:
                repo_full_name = repo_info["full_name"]

                # Step 1: Ask Gemini to generate the app files
                app_files = generate_app_from_brief(payload["brief"])

                # Step 2: Create each generated file in GitHub
                for path, content in app_files.items():
                    create_file(repo_full_name, path, content)

                # Step 3: Add the existing static index.html
                # create_file(repo_full_name, "index.html", index_html_content)

                # Step 4: Enable GitHub Pages
                enable_pages(repo_full_name)

                print("\n✅ Project generated, committed, and deployed successfully!")
                return {"message": "Task recieved and completed", "data": payload} 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)