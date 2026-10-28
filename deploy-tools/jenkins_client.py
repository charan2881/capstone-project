import json
import os
import subprocess
import urllib.error
import urllib.request


def get_jenkins_settings():
    """Read Jenkins settings from environment variables."""
    url = os.environ.get("JENKINS_URL")
    username = os.environ.get("JENKINS_USER")
    token = os.environ.get("JENKINS_TOKEN")

    if not all([url, username, token]):
        raise ValueError(
            "Set JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN "
            "in your terminal first."
        )

    return url.rstrip("/"), username, token


def jenkins_request(path, method="GET"):
    """Send an authenticated request to Jenkins."""
    base_url, username, token = get_jenkins_settings()

    from urllib.parse import quote
    credentials = f"{username}:{token}".encode("utf-8")
    import base64

    auth = base64.b64encode(credentials).decode("ascii")

    request = urllib.request.Request(
        f"{base_url}{path}",
        method=method,
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}

    except urllib.error.HTTPError as error:
        if error.code == 403 and method == "POST":
            raise RuntimeError(
                "Jenkins may require a CSRF crumb. "
                "We will add crumb handling next."
            ) from error

        raise RuntimeError(
            f"Jenkins request failed with HTTP {error.code}."
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Unable to connect to Jenkins: {error.reason}"
        ) from error


def get_job_status():
    """Return the latest Jenkins build status."""
    job = jenkins_request(
        "/job/capstone-project/api/json"
        "?tree=name,lastBuild[number,result,building,url]"
    )

    latest = job.get("lastBuild") or {}

    print("\n===== Jenkins Job Status =====")
    print(f"Job:          {job.get('name', 'Unknown')}")
    print(f"Last build:   #{latest.get('number', 'None')}")
    print(f"Build result: {latest.get('result') or 'RUNNING/UNKNOWN'}")
    print(f"Building:     {latest.get('building', 'Unknown')}")
    print(f"Build URL:    {latest.get('url', 'Unknown')}")


def trigger_deployment():
    """Trigger the existing Jenkins deployment pipeline."""
    jenkins_request(
        "/job/capstone-project/build",
        method="POST",
    )
    print("Deployment pipeline triggered successfully.")
    print("Open Jenkins to follow the build progress.")
