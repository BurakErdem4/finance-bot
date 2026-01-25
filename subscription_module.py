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
        repo_name = get_secret("GITHUB_REPO") 
        if not repo_name:
            repo_name = "BurakErdem4/finance-bot"
            
        repo = g.get_repo(repo_name)
        return repo, None
    except Exception as e:
        return None, str(e)

def get_subscribers():
    """
    Fetches the subscribers.json from the repo.
    Returns the list of subscriber objects: [{"email": "...", "daily": bool, "weekly": bool}]
    """
    repo, error = get_repo_handler()
    data = {"subscribers": []}
    
    if not repo:
        print(f"Repo Error: {error}")
        # Fallback for local dev if file exists
        if os.path.exists("subscribers.json"):
            try:
                with open("subscribers.json", "r") as f:
                    content = json.load(f)
                    # Support legacy migration on read if needed, but better to enforce new structure
                    return content.get("subscribers", [])
            except:
                return []
        return []

    try:
        contents = repo.get_contents("subscribers.json")
        data = json.loads(contents.decoded_content.decode())
        return data.get("subscribers", [])
    except Exception as e:
        print(f"File Error: {e}")
        return []

def add_subscriber(email, daily=True, weekly=True):
    """
    Adds or updates a subscriber with preferences.
    """
    repo, error = get_repo_handler()
    if not repo:
        # Fallback logic for local testing without git perm? 
        # For now, return error as this is crucial.
        # Actually, let's allow partial success if local file can be written? 
        # No, consistent behavior is better.
        return False, f"GitHub bağlantı hatası: {error}"
        
    try:
        # 1. Get current file
        sha = None
        data = {"subscribers": []}
        
        try:
            contents = repo.get_contents("subscribers.json")
            data = json.loads(contents.decoded_content.decode())
            sha = contents.sha
        except:
            # File doesn't exist or is empty
            pass
            
        # 2. Update/Add Logic
        sub_list = data.get("subscribers", [])
        
        # Check if exists
        existing_user = next((s for s in sub_list if s["email"] == email), None)
        
        if existing_user:
            # Update preferences
            existing_user["daily"] = daily
            existing_user["weekly"] = weekly
            msg = "Abonelik tercihleri güncellendi."
        else:
            # Add new
            sub_list.append({
                "email": email,
                "daily": daily,
                "weekly": weekly
            })
            msg = "Abonelik başarıyla oluşturuldu."
            
        data["subscribers"] = sub_list
        
        # 3. Commit Update
        new_content = json.dumps(data, indent=4)
        commit_msg = f"Update subscriber {email} [skip ci]"
        
        if sha:
            repo.update_file("subscribers.json", commit_msg, new_content, sha)
        else:
            repo.create_file("subscribers.json", commit_msg, new_content)
            
        return True, msg
        
    except Exception as e:
        return False, f"İşlem hatası: {str(e)}"
