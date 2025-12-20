import os
import json
import requests
import base64
from enum import Enum

import boto3


class Event(Enum):
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"


# パラメータストアから webhook url を取得
def get_webhook_url() -> str:
    ssm_parameter_path = os.getenv("SSM_PARAMETER_PATH")
    if not ssm_parameter_path:
        raise RuntimeError("SSM_PARAMETER_PATH is not set")

    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    if not aws_session_token:
        raise RuntimeError("AWS_SESSION_TOKEN is not set")

    headers = {"X-Aws-Parameters-Secrets-Token": aws_session_token}
    url = "http://localhost:2773/systemsmanager/parameters/get"
    params = {
        "name": ssm_parameter_path,
    }

    res = requests.get(url, headers=headers, params=params, timeout=3)
    res.raise_for_status()

    data = res.json()
    return data["Parameter"]["Value"]


def lambda_handler(event, context):
    get_webhook_url()

    header_event: dict = event.get("headers", {}).get("X-GitHub-Event", "")

    if not header_event in (event.value for event in Event):
        return {"statusCode": 200, "body": f"Unexcepted event: {header_event}"}

    event_body: str = event.get("body", {})

    try:
        if event.get("isBase64Encoded", False):
            event_body = base64.b64decode(event_body).decode("utf-8")
        body = json.loads(event_body)

        if not body:
            return {"statusCode": 400, "body": "Empty body"}
    except Exception as e:
        print("Failed to parse JSON:", e)
        return {"statusCode": 400, "body": "Invalid JSON"}

    if header_event == Event.PULL_REQUEST.value:
        action = body.get("action", "")
        if action != "opened":
            return {
                "statusCode": 200,
                "body": f"Unexcepted event action: {header_event}: {action}",
            }

        title = body.get("pull_request", {}).get("title")
        url = body.get("pull_request", {}).get("html_url")
        repository_name = (
            body.get("pull_request", {}).get("base", {}).get("repo", {}).get("name")
        )

        try:
            assert title and url and repository_name
        except AssertionError as e:
            return {"statusCode": 400, "body": f"invalid body: {e}"}

        message = f"[[{repository_name}] New Pull Request: {title}]({url})"
    elif header_event in [Event.ISSUES.value, Event.ISSUE_COMMENT.value]:
        action = body.get("action", "")
        if action != "created":
            return {
                "statusCode": 200,
                "body": f"Unexcepted event action: {header_event}: {action}",
            }
        # repository_owner = body.get("repository", {}).get("owner", {}).get("login", "")
        # comment_user = body.get("issue", {}).get("user", {}).get("login", "")

        # if repository_owner == comment_user:
        #     return {"statusCode": 200, "body": f"The commenter is owner."}

        title = body.get("issue", {}).get("title")
        url = body.get("issue", {}).get("html_url")
        repository_name = body.get("repository", {}).get("name")
        comment = body.get("comment", {}).get("body")

        try:
            assert title and url and repository_name and comment
        except AssertionError as e:
            return {"statusCode": 400, "body": f"invalid body: {e}"}

        message = (
            f"[[{repository_name}] New Pull Request: {title}]({url})<br />{comment}"
        )
    else:
        return {"statusCode": 200, "body": f"Unexcepted event: {header_event}"}

    try:
        request_body = {
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True,
                                "markdown": True,
                            }
                        ],
                    },
                }
            ]
        }

        res = requests.post(
            WEBHOOK_URL, headers={"Content-Type": "application/json"}, json=request_body
        )
        res.raise_for_status()
    except Exception as e:
        print("Unexcept Error")
        return {"statusCode": 500, "body": "Unexcept Error"}

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": message,
            }
        ),
    }
