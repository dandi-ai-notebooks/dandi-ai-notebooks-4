#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
import sys

def run_command(command, cwd=None):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd,
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {command}")
        raise

def has_changes(repo_path):
    """Check if repository has any changes"""
    output = run_command('git status --porcelain', cwd=repo_path)
    return bool(output)

def show_changes(repo_path):
    """Show git changes in the repository"""
    output = run_command('git status', cwd=repo_path)
    print(f"\nChanges in {repo_path}:")
    print(output)

def get_user_confirmation():
    """Get user confirmation for git operations"""
    while True:
        response = input("\nDo you want to commit and push these changes? (y/n): ").lower()
        if response in ['y', 'n']:
            return response == 'y'
        print("Please enter 'y' or 'n'")

def ensure_gitignore(repo_path):
    """Ensure .gitignore exists with required entries"""
    gitignore_path = os.path.join(repo_path, '.gitignore')
    required_entries = ['__pycache__', 'core.*']

    # Read existing entries or create new file
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            entries = set(line.strip() for line in f if line.strip())
    else:
        entries = set()

    # Add missing entries
    missing_entries = [entry for entry in required_entries if entry not in entries]
    if missing_entries:
        with open(gitignore_path, 'a') as f:
            if entries and not f.tell():  # If file exists but no newline at end
                f.write('\n')
            f.write('\n'.join(missing_entries) + '\n')
        print(f"Updated .gitignore in {repo_path}")

def process_repository(repo_path):
    """Process a single repository"""
    if not os.path.exists(os.path.join(repo_path, '.git')):
        print(f"{repo_path} is not a git repository, skipping...")
        return

    # Ensure .gitignore is properly set up
    ensure_gitignore(repo_path)

    if not has_changes(repo_path):
        print(f"\nNo changes in {repo_path}")
        return

    show_changes(repo_path)

    if not get_user_confirmation():
        print("Skipping this repository")
        return

    print(f"\nProcessing {repo_path}...")
    try:
        # Add all changes
        run_command('git add .', cwd=repo_path)

        # Commit changes
        run_command('git commit -m "updates"', cwd=repo_path)

        # Push changes
        run_command('git push', cwd=repo_path)

        print("Successfully processed repository")
    except subprocess.CalledProcessError:
        print("Failed to process repository")
        return

def main():
    dandiset_repos = Path('dandiset_repos')
    if not dandiset_repos.exists():
        print("Error: dandiset_repos directory not found")
        sys.exit(1)

    # Process each subdirectory in dandiset_repos
    for repo_dir in dandiset_repos.iterdir():
        if repo_dir.is_dir():
            process_repository(repo_dir)

if __name__ == "__main__":
    main()
