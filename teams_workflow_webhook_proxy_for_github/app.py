import os
import json
import requests
import base64


TARGET_EVENT: list[str] = ["issues", "issue_comment"]
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL")


def lambda_handler(event, context):
    header: dict = event.get("headers", {})

    if not header.get("X-GitHub-Event", "") in TARGET_EVENT:
        return {"statusCode": 400, "body": "Illegal event"}

    event_body: str = event.get("body", {})

    try:
        if event.get("isBase64Encoded", False):
            event_body = base64.b64decode(event_body).decode("utf-8")
        body = json.loads(event_body)
    except Exception as e:
        print("Failed to parse JSON:", e)
        return {"statusCode": 400, "body": "Invalid JSON"}

    if not body:
        return {"statusCode": 400, "body": "Empty body"}

    repository_name = body.get("repository", {}).get("full_name")
    url = body.get("comment", {}).get("html_url")
    comment = body.get("comment", {}).get("body")
    title = body.get("issue", {}).get("title")

    try:
        assert (
            repository_name != None
            and repository_name != None
            and comment != None
            and url != None
        )
    except AssertionError as e:
        return {"statusCode": 400, "body": f"invalid body: {e}"}

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
                                "text": f"[[{repository_name}] New issue event: {title}]({url})<br />{comment}",
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
        return {"statusCode": 500, "body": f"Unexcept Error"}

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "OK",
            }
        ),
    }
