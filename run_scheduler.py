import os
import sys

# Ensure the current directory is in the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mail_module import send_daily_report, get_app_secret

def main():
    print("Starting Headless Finance Report...")
    
    # 1. Get Target Email
    # Try getting from env, or fallback to GMAIL_USER (sending to self)
    target_email = get_app_secret("TARGET_EMAIL")
    if not target_email:
        target_email = get_app_secret("GMAIL_USER")
        
    if not target_email:
        print("Error: Target email not found in env vars (TARGET_EMAIL or GMAIL_USER).")
        sys.exit(1)
        
    print(f"Target Email: {target_email}")
    
    # 2. Determine Report Type based on arguments or time
    # Defaulting to "Günlük" (Daily)
    report_type = "Günlük"
    if len(sys.argv) > 1:
        report_type = sys.argv[1] # e.g. python run_scheduler.py Haftalık
        
    print(f"Report Type: {report_type}")
    
    # 3. Send Report
    success, message = send_daily_report(target_email, report_type)
    
    if success:
        print(f"Success: {message}")
    else:
        print(f"Failed: {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()
