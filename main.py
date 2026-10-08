#!/usr/bin/env python3
"""GitHub Roast and Rescue - Main entry point.

Takes a GitHub username and provides honest, funny (but not cruel)
feedback with actionable improvement advice.

Security Review (security-review skill integration):
- Username validated against GitHub naming conventions before API call
- No private data requested or stored - only public profile/repo data
- API failures handled gracefully (rate limit, user not found)
- Rate limiting respected (60/hr unauthenticated)
- Username @ prefix stripped safely; invalid formats rejected
"""

import re
import sys
import argparse
from github_client import GitHubClient
from analyzer import analyze_profile
from output import format_output

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$")


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Roast and Rescue - Analyze a GitHub profile"
    )
    parser.add_argument(
        "username",
        nargs="?",
        default=None,
        help="GitHub username to analyze (positional)",
    )
    parser.add_argument(
        "-u", "--username",
        dest="username_flag",
        default=None,
        help="GitHub username to analyze (flag syntax)",
    )
    parser.add_argument(
        "--antigravity",
        action="store_true",
        help="Engage Python zero-gravity easter egg (xkcd #353)",
    )
    args = parser.parse_args()

    if args.antigravity:
        print("\n🕊️  ANTIGRAVITY ENGAGED  🕊️")
        print("Zero-gravity mode enabled — floating above the grind.")
        try:
            import antigravity  # Python standard library easter egg
        except Exception:
            pass
        print("⚡ Built with Claude + OpenCode + Antigravity\n")
        return

    raw_username = args.username_flag or args.username
    if not raw_username or not raw_username.strip():
        print("Error: Username is required (e.g. python main.py octocat or python main.py --username octocat)", file=sys.stderr)
        sys.exit(1)

    username = raw_username.strip().lstrip("@")
    if not USERNAME_REGEX.match(username):
        print(f"Error: Invalid GitHub username format '{username}'. GitHub usernames may only contain alphanumeric characters and hyphens.", file=sys.stderr)
        sys.exit(1)

    # Step 1: Fetch GitHub data
    client = GitHubClient()
    profile_data = client.get_user_profile(username)
    repos_data = client.get_user_repos(username)
    events_data = client.get_recent_activity(username)

    # Check if data fetching failed (rate limited or user not found)
    if profile_data is None:
        print(f"Error: Could not fetch data for '@{username}'.", file=sys.stderr)
        print("This may be due to GitHub API rate limiting. Try again later.", file=sys.stderr)
        sys.exit(1)

    if repos_data is None:
        print(f"Warning: Repo data could not be fetched for '@{username}'.", file=sys.stderr)
        repos_data = []

    # Step 2: Analyze with Claude
    analysis = analyze_profile(profile_data, repos_data, username, events_data=events_data)

    # Step 3: Format and display output
    format_output(analysis)


if __name__ == "__main__":
    main()