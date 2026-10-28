
import json
from pathlib import Path

CONFIG_FILE = Path("deploy-tool.json")

DEFAULT_CONFIG = {
    "aws_region": "eu-north-1",
    "ecr_repository": "863555332085.dkr.ecr.eu-north-1.amazonaws.com/aws-deployment-capstone",
    "ecs_cluster": "aws-deployment-cluster",
    "ecs_service": "aws-deployment-service",
    "task_family": "aws-deployment-task",
    "container_name": "aws-deployment-container",
    "container_port": 5000
}


def init_config():
    """Create a deployment configuration file."""
    if CONFIG_FILE.exists():
        print(f"Configuration already exists: {CONFIG_FILE}")
        return

    CONFIG_FILE.write_text(
        json.dumps(DEFAULT_CONFIG, indent=4),
        encoding="utf-8"
    )

    print(f"Configuration created: {CONFIG_FILE}")


def load_config():
    """Load deployment configuration."""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            "Configuration not found. Run 'deploy-tool init' first."
        )

    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def show_config():
    """Display deployment configuration."""
    config = load_config()
    print(json.dumps(config, indent=4))


def update_config(key, value):
    """Update a configuration setting."""
    config = load_config()

    if key not in config:
        raise ValueError(f"Unknown configuration key: {key}")

    if key == "container_port":
        value = int(value)

    config[key] = value

    CONFIG_FILE.write_text(
        json.dumps(config, indent=4),
        encoding="utf-8"
    )

    print(f"Updated {key} successfully.")
