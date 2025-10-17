from google import generativeai as genai
import os
import requests
import json
import base64
# ==============================================================
# --- Load environment variables ---
GITHUB_SECRET = os.getenv("GITHUB_SECRET")
if not GITHUB_SECRET:
    raise ValueError("Please set the GITHUB_SECRET environment variable")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")

# --- Configure Gemini ---
genai.configure(api_key=GEMINI_API_KEY)
API_URL = "https://api.github.com"


def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No valid JSON found")


def generate_app_from(brief):
    """
    Sends the project brief to Gemini and gets back generated code.
    Expects the model to return JSON: {"files": {"filename": "content", ...}}
    """
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = f"""
    You are an expert full-stack developer.
    Build a minimal, interactive working application according to the following brief:
    ---
    {brief}
    ---

    Return ONLY valid JSON with this structure excluding extra non-JSON characters: the backticks and the json\n preamble, as well as potential invisible characters (like a non-breaking space) that might be present in the original input, specifically the spaces used for indentation.

:
    {{
      "files": {{
        "README.md": '<complete markdown readme with sections: Summary, Setup, Usage, Code Explanation, version update information with date and version number and changes, License>'
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
            json_text = json_text.replace('\xa0', ' ')
        app_json = json.loads(json_text)
        files = app_json.get("files", {})
        print(f"✅ Gemini generated {len(files)} file(s).")
        return files
    except Exception as e:
        print("⚠️ Error parsing Gemini output:", e)
        print("Raw response:\n", response.text)
        return {"main.py": "# Gemini output error\nprint('Hello World')"}
    
def upload_attachments(repo_full_name, attachments):
    """
    Decodes and uploads attachments (e.g., images) to the GitHub repository.
    """
    for att in attachments:
        name = att.get("name")
        url = att.get("url")

        if not name or not url:
            print(f"⚠️ Skipping invalid attachment: {att}")
            continue

        # Extract Base64 data from "data:image/png;base64,..."
        match = re.search(r"base64,(.*)", url)
        if not match:
            print(f"⚠️ No base64 content found in {name}")
            continue

        base64_data = match.group(1)
        try:
            binary_content = base64.b64decode(base64_data)
            encoded_content = base64.b64encode(binary_content).decode()

            upload_url = f"{API_URL}/repos/{repo_full_name}/contents/{name}"
            headers = {
                "Authorization": f"token {GITHUB_SECRET}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "message": f"Add attachment {name}",
                "content": base64.b64encode(binary_content).decode(),
                "branch": "main"
            }

            response = requests.put(upload_url, headers=headers, data=json.dumps(data))
            if response.status_code in (201, 200):
                return {"status_code": {response.status_code}, "message": f"🖼️ Uploaded attachment '{name}' successfully."}
            else:
                return{"status_code": {response.status_code}, "message": f"⚠️ Failed to upload '{name}': {response.content}"}

        except Exception as e:
            return {"status_code": {response.status_code}, "message": f"❌ Error processing {name}: {e}"}    

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
        "description": repo_description,
        "private": False,
        "license_template": "mit",
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        full_name = response.json()["full_name"]
        print(f"✅ Repository '{full_name}' created successfully. Response code: {response.status_code} ")
        # get commit sha of main branch
        sha_url = f"{API_URL}/repos/{full_name}/git/refs/heads/main"
        sha_response = requests.get(sha_url, headers=headers)
        if sha_response.status_code == 200:
            sha = sha_response.json()["object"]["sha"]
        return response.json()
    else:
        print(f"❌ Error creating repository: {response.content}, Response code: {response.status_code}")
        return None

# Update repositry files and commit
def update_repo(path, file_path, content, sha):
    """Updates an existing file in the repository."""
    url = f"{API_URL}/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }    
    encoded_content = base64.b64encode(content.encode()).decode()
    data = {
        "name": file_path,
        "message": f"Update {file_path}",
        "content": encoded_content,
        "branch": "main",
        "sha": sha,
    }  
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print(f"📄 File '{file_path}' updated successfully., Response code = {response.status_code}" )
        return response.json()
    else:
        print(f"⚠️ Error updating file '{file_path}': {response.content}")
        return response.json()

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
        return response.json()
    else:
        print(f"⚠️ Error creating file '{file_path}': {response.content}")
        return response.json()


def get_sha():
    """Get the latest commit SHA of the main branch."""
    url = f"{API_URL}/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        repos = response.json()
        if repos:
            repo_full_name = repos[0]["full_name"]
            sha_url = f"{API_URL}/repos/{repo_full_name}/git/refs/heads/main"
            sha_response = requests.get(sha_url, headers=headers)
            if sha_response.status_code == 200:
                sha = sha_response.json()["object"]["sha"]
                return sha
            else:
                print("⚠️ Error getting SHA:", sha_response.content)
                return None
        else:
            print("⚠️ No repositories found.")
            return None
    else:
        print("⚠️ Error fetching repositories:", response.content)
        return None     
    
# Update repo files and commit  
def update_file(repo_full_name, file_path, content):
    """Updates an existing file in the repository."""
    headers = {
        "Authorization": f"token {GITHUB_SECRET}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # Get file metadata to retrieve the current sha
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info['sha']
    else:
        print("Failed to get file info:", response.content)
        return None
    
    encoded_content = base64.b64encode(content.encode()).decode()
    data = {
        "message": f"Update {file_path}",
        "content": encoded_content,
        "branch": "main",
        "sha": sha,
    }
    
    response = requests.put(url, headers=headers, data=json.dumps(data))
    if response.status_code in [200, 201]:
        print(f"📄 File '{file_path}' updated successfully.")
        return response.json()
    else:
        print(f"⚠️ Error updating file '{file_path}': {response.content}")
        return response.json()


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
    return secret == os.getenv("SECRET")

def evaluate_task(payload: dict, repo_info, sha, repo_full_name, round):
        if payload.get("evaluation_url"):
            post_message = {
                "email": f"{payload.get('email')}",
                "task": f"{payload.get('task')}",
                "round": round,
                "nonce": f"{payload.get('nonce')}",
                "repo_url": f"{repo_info.get('html_url')}",
                "commit_sha": f"{sha}",
                "page_url": f"https://{repo_full_name.split('/')[0]}.github.io/{repo_full_name.split('/')[1]}/",
            }
            try:
                eval_response = requests.post(payload["evaluation_url"], json=post_message)
                if eval_response.status_code == 200:
                    return{"user_code": 200, "message": "📬 Evaluation URL notified successfully."}
                else:
                    print(f"⚠️ Error notifying evaluation URL: {eval_response.content}")
            except Exception as e:
                print(f"⚠️ Exception notifying evaluation URL: {e}")

        if round == 1:
            print(f"\n✅ Project (Round {round}  - code generated, committed, and deployed successfully!")
        else:
            print(f"\n✅ Project (Round {round}  - code updated, committed, and deployed successfully!")

        return {"user_code": 200, "message": "Task recieved and completed", "data": payload} 


def round1(payload: dict):
    #  Save round 1 payload to file
    with open("round1_payload.json", "w") as f:
        json.dump(payload, f, indent=2)

    repo_info = create_repo(payload)
    if repo_info:
        repo_full_name = repo_info["full_name"]

        # Step 1: Ask Gemini to generate the app files
        app_files = generate_app_from(payload["brief"])

        # Step 2: Create each generated file in GitHub
        for path, content in app_files.items():
            create_file(repo_full_name, path, content)

        # Step 3: Add attachements (if any)
        if payload.get("attachments"):
            upload_attachments(repo_full_name, payload["attachments"])
        # create_file(repo_full_name, "index.html", index_html_content)

        # Step 4: Enable GitHub Pages
        enable_pages(repo_full_name)
        return evaluate_task(payload, repo_info, get_sha(), repo_full_name, 1)
        

def get_first_round_brief():
    with open("round1_payload.json", "r") as f:
        payload = json.load(f)
    return payload["brief"]

#  round 2: Handle improvements, bug fixes, etc.
def round2(payload: dict):
    print("🔄 Starting round 2 updates...")
    #  Save round 2 payload to file
    with open("round2_payload.json", "w") as f:
        json.dump(payload, f, indent=2)    
    
    repo_name= payload["task"].lower()
    owner = payload["email"].split('@')[0]
    repo_full_name = f"{owner}/{repo_name}"
    first_round_brief = get_first_round_brief()
    brief = f"{first_round_brief}. Update: {payload['brief']}"
    print("🔄 Updated brief for round 2:", brief)
    app_files = generate_app_from(brief)
    print(f"🔄 Generated {len(app_files)} updated file(s) for round 2.")

    # Step 2: Create each generated file in GitHub
    for file, content in app_files.items():
        update_file(repo_full_name, file, content)
    print("\n🔄 Project (round 2) updated successfully!")
    return evaluate_task(payload, {}, get_sha(), repo_full_name, 2)
