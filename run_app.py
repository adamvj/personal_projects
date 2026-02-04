import sys
import os
from streamlit.web import cli as stcli

def main():
    # Absolute path to the user's script
    # script_path = "/Users/adamjose/Library/Messages/Attachments/01/01/030FA061-4C29-4B75-80B4-0D87FB573EB5/SalaryCap.py"
    
    # Use relative path so it works in the repo
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "SalaryCap.py")
    
    # Construct the argv for streamlit run
    sys.argv = ["streamlit", "run", script_path]
    
    print(f"Launching Streamlit App: {script_path}")
    print("Press Ctrl+C to stop the app.")
    
    # Run streamlit
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
