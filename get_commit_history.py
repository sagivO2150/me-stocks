#!/usr/bin/env python3
import subprocess
import os
from pathlib import Path

def get_commit_history():
    """
    Script to extract all commit history and save to a text file.
    This will override the previous file each time it runs.
    """
    print("Extracting commit history...")
    
    # Get the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    
    # Define the output file path
    output_file = script_dir / "commit history.txt"
    
    try:
        # Run git log command with hash, subject, and body
        # %H = commit hash, %s = subject (title), %b = body (description)
        result = subprocess.run(
            ["git", "log", "--pretty=format:%H%n%s%n%b%n---COMMIT_SEPARATOR---"],
            capture_output=True,
            text=True,
            check=True,
            cwd=script_dir
        )
        
        # Write to file (overwriting previous content)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        # Count commits for feedback
        commit_count = result.stdout.count('---COMMIT_SEPARATOR---')
        
        print(f"Commit history successfully saved to: {output_file}")
        print(f"Total commits found: {commit_count}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to extract commit history. Make sure you're in a git repository.")
        print(f"Git error: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    get_commit_history()
