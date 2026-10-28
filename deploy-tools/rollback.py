import json
import subprocess


def run_aws_command(command):
    """Run an AWS CLI command and return its JSON output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout.strip() else {}

    except FileNotFoundError:
        raise RuntimeError("AWS CLI was not found. Install AWS CLI first.")

    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or str(error)
        raise RuntimeError(f"AWS CLI command failed: {message}")


def rollback_deployment(config):
    """Roll back an ECS service to the previous task definition revision."""

    region = config["aws_region"]
    cluster = config["ecs_cluster"]
    service_name = config["ecs_service"]
    task_family = config["task_family"]

    service_data = run_aws_command([
        "aws", "ecs", "describe-services",
        "--cluster", cluster,
        "--services", service_name,
        "--region", region,
        "--output", "json"
    ])

    services = service_data.get("services", [])
    if not services:
        raise RuntimeError(f"ECS service '{service_name}' was not found.")

    current_task_definition = services[0]["taskDefinition"]
    current_revision = int(current_task_definition.rsplit(":", 1)[1])

    task_data = run_aws_command([
        "aws", "ecs", "list-task-definitions",
        "--family-prefix", task_family,
        "--status", "ACTIVE",
        "--sort", "DESC",
        "--region", region,
        "--output", "json"
    ])

    task_definitions = task_data.get("taskDefinitionArns", [])
    previous_task_definition = next(
        (
            arn for arn in task_definitions
            if int(arn.rsplit(":", 1)[1]) < current_revision
        ),
        None
    )

    if not previous_task_definition:
        raise RuntimeError(
            f"No previous active revision was found for '{task_family}'."
        )

    print("\n===== ECS Rollback Preview =====")
    print(f"Cluster:          {cluster}")
    print(f"Service:          {service_name}")
    print(f"Current revision: {current_task_definition.rsplit('/', 1)[-1]}")
    print(f"Target revision:  {previous_task_definition.rsplit('/', 1)[-1]}")

    confirmation = input(
        "\nRoll back to the previous revision? Type 'yes' to continue: "
    ).strip().lower()

    if confirmation != "yes":
        print("Rollback cancelled. No changes were made.")
        return

    run_aws_command([
        "aws", "ecs", "update-service",
        "--cluster", cluster,
        "--service", service_name,
        "--task-definition", previous_task_definition,
        "--region", region,
        "--output", "json"
    ])

    print("\nRollback requested successfully.")
    print("ECS will replace tasks as the service deployment progresses.")
    print("Run 'python deploy-tools/cli.py status' to check deployment status.")