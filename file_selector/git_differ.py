import requests
import subprocess
from urllib.parse import urlparse
from base64 import b64encode


def get_repo_info(github_url):
    """Extract owner and repo name from GitHub URL"""
    path = urlparse(github_url).path.strip("/")
    owner, repo = path.split("/")[:2]
    return owner, repo


def get_git_credentials():
    """Get GitHub credentials from local Git config"""
    try:
        # Try to get the GitHub username
        username = (
            subprocess.check_output(["git", "config", "--get", "user.name"], stderr=subprocess.PIPE).decode("utf-8").strip()
        )

        # Try to get the GitHub token/password from credential helper
        git_credentials = subprocess.check_output(
            ["git", "credential", "fill"],
            input=b"protocol=https\nhost=github.com\n\n",
            stderr=subprocess.PIPE,
        ).decode("utf-8")

        # Parse the credentials output
        cred_dict = dict(line.split("=", 1) for line in git_credentials.splitlines() if "=" in line)
        password = cred_dict.get("password", "")

        if username and password:
            return {"Authorization": f'Basic {b64encode(f"{username}:{password}".encode()).decode()}'}

    except subprocess.CalledProcessError:
        pass

    return {}


def get_branch_diff(github_url, branch_name, output_file="diff_output.txt"):
    """
    Get the full diff of a GitHub branch and save it to a file in the specified format

    Args:
        github_url (str): URL of the GitHub repository
        branch_name (str): Name of the branch to compare against main/master
        output_file (str): Name of the output file
    """
    owner, repo = get_repo_info(github_url)

    # Get authentication headers from Git config
    headers = get_git_credentials()

    # First, try to compare against 'main'
    base_branch = "main"
    compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base_branch}...{branch_name}"

    response = requests.get(compare_url, headers=headers)

    # If main doesn't exist, try master
    if response.status_code == 404:
        base_branch = "master"
        compare_url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base_branch}...{branch_name}"
        response = requests.get(compare_url, headers=headers)

    if response.status_code == 404:
        raise Exception(
            f"Repository or branch not found. Please check:\n"
            f"1. The repository exists and is accessible\n"
            f'2. The branch name "{branch_name}" is correct\n'
            f"3. You have the necessary permissions\n"
            f"4. Your Git credentials are properly configured"
        )
    elif response.status_code != 200:
        raise Exception(f"GitHub API error (Status code: {response.status_code})\n" f"Response: {response.text}")

    diff_data = response.json()

    with open(output_file, "w", encoding="utf-8") as f:
        for file in diff_data["files"]:
            filename = file["filename"]
            patch = file.get("patch", "")

            if patch:
                # Write filename
                f.write(f"{filename}\n\n")

                # Write code block
                f.write("```\n")
                f.write(patch)
                f.write("\n```\n\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Get GitHub branch diff and save to file")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("branch_name", help="Branch name to compare")
    parser.add_argument("--output", default="diff_output.txt", help="Output file name")

    args = parser.parse_args()

    try:
        get_branch_diff(args.repo_url, args.branch_name, args.output)
        print(f"Diff has been saved to {args.output}")
    except Exception as e:
        print(f"Error: {str(e)}")
