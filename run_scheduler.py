import os
import sys

# Ensure the current directory is in the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mail_module import send_newsletter, get_app_secret

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
    from datetime import datetime
    
    # If args provided, force that type (e.g., manual trigger)
    if len(sys.argv) > 1:
        report_type = sys.argv[1] 
        print(f"Forcing Report Type: {report_type}")
        success, message = send_newsletter(target_email, report_type)
        if success:
             print(f"Success: {message}")
        else:
             print(f"Failed: {message}")
             sys.exit(1)
    else:
        # Standard Scheduler Run
        print("Running Standard Scheduler...")
        
        # 1. Send Daily Report (Always)
        print("--- Sending Daily Report ---")
        d_success, d_msg = send_newsletter(target_email, "Günlük")
        print(f"Daily Result: {d_msg}")
        
        # 2. Check for Monday (Weekly Report)
        # Monday is 0
        if datetime.now().weekday() == 0:
            print("--- Monday Detected: Sending Weekly Report ---")
            w_success, w_msg = send_newsletter(target_email, "Haftalık")
            print(f"Weekly Result: {w_msg}")
            
            if not d_success and not w_success:
                sys.exit(1) # Fail if both fail
        else:
            if not d_success:
                sys.exit(1)

if __name__ == "__main__":
    main()
