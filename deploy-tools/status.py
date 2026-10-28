import json
import subprocess


def get_service_status(config):
    """Display the current Amazon ECS service status."""

    command = [
        "aws", "ecs", "describe-services",
        "--cluster", config["ecs_cluster"],
        "--services", config["ecs_service"],
        "--region", config["aws_region"],
        "--output", "json"
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        data = json.loads(result.stdout)
        services = data.get("services", [])

        if not services:
            print("ECS service not found.")
            return

        service = services[0]

        print("\n===== ECS Deployment Status =====")
        print(f"Cluster:          {service['clusterArn'].split('/')[-1]}")
        print(f"Service:          {service['serviceName']}")
        print(f"Status:           {service['status']}")
        print(f"Desired tasks:    {service['desiredCount']}")
        print(f"Running tasks:    {service['runningCount']}")
        print(f"Pending tasks:    {service['pendingCount']}")
        print(f"Task definition:  {service['taskDefinition'].split('/')[-1]}")
        print(f"Deployments:      {len(service['deployments'])}")

        if (
            service["desiredCount"] == service["runningCount"]
            and service["pendingCount"] == 0
        ):
            print("\nResult: Service is running at the desired capacity.")
        else:
            print("\nResult: Service is not yet at the desired capacity.")

    except FileNotFoundError:
        print("AWS CLI was not found. Install AWS CLI and try again.")

    except subprocess.CalledProcessError as error:
        print("Unable to retrieve ECS service status.")
        print(error.stderr)
