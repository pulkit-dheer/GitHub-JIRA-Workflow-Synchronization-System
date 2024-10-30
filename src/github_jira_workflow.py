"""
GitHub-JIRA Workflow Synchronization System

This module integrates JIRA and GitHub to enable seamless workflow automation between pull request management and issue tracking. 
The primary functionalities include:

- Validating pull request titles to ensure they reference a valid JIRA issue key.
- Automatically creating JIRA issues directly from GitHub webhook events for improved task tracking and traceability.
- Generating remote links in JIRA for related pull requests, enabling quick access to the relevant code changes.
- Providing response logging and error handling, ensuring reliable synchronization between platforms.

Configuration:
- Requires JIRA authentication details (`JIRA_EMAIL`, `JIRA_API_TOKEN`) and project metadata (`PROJECT_KEY`, `ISSUE_TYPE_ID`).
- Ensures secure communication with JIRA and GitHub through basic authentication and HTTP methods.

This module powers the collaborative flow in DevOps environments by automating the creation, validation, and linking of GitHub pull requests to JIRA issues, enabling end-to-end traceability across repositories and issue tracking.
"""


import os
import re
import logging
from flask import Flask, request, jsonify
import requests


# Flask app initialize
app = Flask(__name__)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# JIRA API configuration
JIRA_BASE_URL = "https://pulkitdheer.atlassian.net/rest/api/3/issue"
AUTH = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
PROJECT_KEY = "GJ"
ISSUE_TYPE_ID = "10011"



def validate_pull_request_title(title):
    """Validate the pull request title for a valid JIRA issue key."""
    pattern = r'[A-Z]+-\d+'
    match = re.search(pattern, title)
    if not match:
        logger.error("Invalid JIRA issue key in pull request title: %s", title)
        return None
    return match.group()


def check_jira_issue_exists(issue_id):
    """Check if the JIRA issue exists."""
    url = f"{JIRA_BASE_URL}/{issue_id}"
    response = requests.get(url, auth=AUTH, timeout=10)
    return response.status_code == 200


def create_remote_link(issue_id, title, url):
    """Create a remote link in the JIRA issue."""
    link_url = f"{JIRA_BASE_URL}/{issue_id}/remotelink"
    payload = {
        "object": {
            "icon": {
                "url16x16": "https://github.com/favicon.ico"
            },
            "title": title,
            "url": url
        }
    }
    response = requests.request("POST",link_url, json=payload, auth=AUTH, timeout=10)
    return response

def create_jira_issue(summary, description):
    """Create a JIRA issue with summary and description"""    
    url = f"{JIRA_BASE_URL}"
    payload = {
            "fields": {
                "summary": summary,
                "description": {
                    "content": [
                        {
                            "content": [
                                {
                                    "text": description,
                                    "type": "text"
                                }
                            ],
                            "type": "paragraph"
                        }
                    ],
                    "type": "doc",
                    "version": 1
                },
                "issuetype": {
                    "id": ISSUE_TYPE_ID
                },
                "project": {
                    "key": PROJECT_KEY
                }
            }
        }

    response = requests.request("POST", url, json=payload, auth=AUTH, timeout=10)
    return response



@app.route("/createJira", methods=['POST'])
def create_jira():
    """Endpoint to create a JIRA issue from a GitHub webhook event."""
    data = request.json
    try:
        title = data['issue']['title']
        issue_description = data['issue']['body']
        comment = data['comment']['body']
    except KeyError as e:
        logger.error("Missing key in payload: %s", e)
        return jsonify({"message" : "Missing field: {e}"}), 400

    # Validate the command in the comment
    if '/createjira' not in comment:
        logger.warning("Command '/createjira' not found in comment.")
        return jsonify({"message": "Command '/createjira' not found in comment"}), 400


    # Create the Jira issue
    response = create_jira_issue(title, issue_description)

    if response.status_code == 201:
        issue_key = response.json().get("key")
        logger.info("Issue created successfully with key: %s", issue_key)
        return jsonify({"message": "Issue created successfully", "issue_key": issue_key}), 201
    else:
        logger.error("Failed to create issue. Response: %s", response.json())
        return jsonify({
            "message": "Failed to create issue",
            "details": response.json()
        }), response.status_code




@app.route('/createRemoteLink', methods = ["POST"])
def create_remote_link_handler():
    """Handle the creation of remote link for pull requests"""
    data = request.json
    action = data.get('action')

    pull_request_title = data['pull_request']['title']
    pull_request_url = data['pull_request']['html_url']

    if action in ['opened', 'reopened']:
        issue_id = validate_pull_request_title(pull_request_title)
        if issue_id is None:
            return jsonify({"error": "Pull request title must"
                            "include a valid JIRA issue key."}), 400

        if not check_jira_issue_exists(issue_id):
            return jsonify({"error": "JIRA issue does not exist."}), 400

        response = create_remote_link(issue_id, pull_request_title, pull_request_url)
        if response.status_code == 401:
            logger.error('Invalid JIRA credentials.')
            return jsonify({"error": "Invalid JIRA credentials."}), 401

        logger.info("Remote link created successfully for pull request: %s", pull_request_title)
        return jsonify({"message": "Remote link created successfully."}), response.status_code

    if action == 'opened':
        response = create_remote_link(issue_id, pull_request_title, pull_request_url)
        if response.status_code == 401:
            logger.error('Invalid JIRA credentials.')
            return jsonify({"error": "Invalid JIRA credentials."}), 401
        logger.info("Remote link created successfully for pull request: %s", pull_request_title)
        return jsonify({"message": "Remote link created successfully."}), response.status_code

    elif action == 'closed':
        logger.info("Pull request closed: %s ", pull_request_title)
        return jsonify({"message": 'PUll request closed.'}), 200

    elif action == 'synchronize':
        logger.info('Pull request ')

    return jsonify({"error": "Unhandled pull request action."}), 400



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", "9000")), debug=False)
