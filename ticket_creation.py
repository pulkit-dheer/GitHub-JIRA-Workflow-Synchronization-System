import json
from flask import Flask, jsonify, request
import requests
from requests.auth import HTTPBasicAuth

# Flsak app instance
app = Flask(__name__)


@app.route("/createJira", methods = ['POST'])
def create_jira():

    # Get JSON playload form GitHub webhook
    data = request.get_json()
    
    title = data['issue']['title']
    
    
    issue_description = data['issue']['body']

    if 'comment' not in data or 'body' not in data['comment']:
        return jsonify({"message": "No comment found in payload"}), 400
    
    comment = data['comment']['body']

    if '/createjira' not in comment:
        return jsonify({"message": "No comment found in playload"}), 400


    url = "https://user-name.atlassian.net/rest/api/3/issue"

    API_TOKEN = ""

    auth = HTTPBasicAuth('<Your_email>', API_TOKEN)

    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
    }

    payload = json.dumps( {
    "fields": {
        "description": {
        "content": [
            {
            "content": [
                {
                "text": issue_description,
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
        "id": "10011"
        },
        "project": {
        "key": "GJ"
        },
        "summary": title,
    },
    "update": {}
    } )


    response = requests.request(
    "POST",
    url,
    data=payload,
    headers=headers,
    auth=auth
    )

    if response.status_code == 201:
        return jsonify({"message": "Issue created successfully", "issue_key": response.json().get("key")}), 201
    else:
        return jsonify({"message": "Failed to create issue", "details": response.json()}), response.status_code



app.run('0.0.0.0', port="9000")