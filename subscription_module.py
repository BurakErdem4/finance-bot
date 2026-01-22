from github import Github
import json
import os
import streamlit as st

# Helper to get secrets safely (reused logic)
def get_secret(key):
    val = os.environ.get(key)
    if val: return val
    try:
        return st.secrets[key]
    except:
        return None

def get_repo_handler():
    """
    Authenticates with GitHub and returns the repository object.
    Requires GITHUB_TOKEN in secrets/env.
    """
    token = get_secret("GITHUB_TOKEN")
    if not token:
        return None, "GITHUB_TOKEN bulunamadı."
        
    try:
        g = Github(token)
        # Getting the repo name from env or secrets, or assuming known structure
        # Best practice: define REPO_NAME in secrets
        repo_name = get_secret("GITHUB_REPO") 
        if not repo_name:
            # Fallback attempts if specific format exists, otherwise error
            # For this specific user path: BurakErdem4/finance-bot seems correct based on corpus name
            repo_name = "BurakErdem4/finance-bot"
            
        repo = g.get_repo(repo_name)
        return repo, None
    except Exception as e:
        return None, str(e)

def get_subscribers():
    """
    Fetches the subscribers.json from the repo.
    Returns a list of emails.
    """
    repo, error = get_repo_handler()
    if not repo:
        print(f"Repo Error: {error}")
        # Fallback for local dev if file exists
        if os.path.exists("subscribers.json"):
            with open("subscribers.json", "r") as f:
                return json.load(f).get("emails", [])
        return []

    try:
        contents = repo.get_contents("subscribers.json")
        data = json.loads(contents.decoded_content.decode())
        return data.get("emails", [])
    except Exception as e:
        print(f"File Error: {e}")
        # If file doesn't exist on remote, return empty
        return []

def add_subscriber(email):
    """
    Adds a new email to subscribers.json and commits changes to GitHub.
    """
    repo, error = get_repo_handler()
    if not repo:
        return False, f"GitHub bağlantı hatası: {error}"
        
    try:
        # 1. Get current file
        try:
            contents = repo.get_contents("subscribers.json")
            data = json.loads(contents.decoded_content.decode())
            sha = contents.sha
        except:
            # File doesn't exist, create proper structure
            data = {"emails": []}
            sha = None
        
        # 2. Add Email
        if email in data["emails"]:
            return False, "Bu email zaten abone listesinde var."
            
        data["emails"].append(email)
        
        # 3. Commit Update
        new_content = json.dumps(data, indent=4)
        commit_msg = f"Add subscriber {email} [skip ci]"
        
        if sha:
            repo.update_file("subscribers.json", commit_msg, new_content, sha)
        else:
            repo.create_file("subscribers.json", commit_msg, new_content)
            
        return True, "Abonelik başarıyla tamamlandı!"
        
    except Exception as e:
        return False, f"İşlem hatası: {str(e)}"
