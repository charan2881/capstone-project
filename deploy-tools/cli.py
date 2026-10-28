import argparse
import sys

from config import init_config, show_config, update_config, load_config
from status import get_service_status
from jenkins_client import get_job_status, trigger_deployment
from rollback import rollback_deployment


def main():
    parser = argparse.ArgumentParser(
        prog="deploy-tool",
        description="CLI tool to deploy applications to AWS ECS"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    subparsers.add_parser(
        "init",
        help="Initialize deployment configuration"
    )

    config_parser = subparsers.add_parser(
        "config",
        help="View or update deployment configuration"
    )
    config_parser.add_argument("key", nargs="?", help="Configuration key")
    config_parser.add_argument("value", nargs="?", help="New configuration value")

    subparsers.add_parser(
        "status",
        help="Check Amazon ECS deployment status"
    )

    subparsers.add_parser(
        "jenkins-status",
        help="Check the latest Jenkins build status"
    )

    subparsers.add_parser(
        "deploy",
        help="Trigger the Jenkins deployment pipeline"
    )

    subparsers.add_parser(
        "rollback",
        help="Roll back ECS to the previous task definition revision"
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            init_config()

        elif args.command == "config":
            if args.key and args.value:
                update_config(args.key, args.value)
            elif args.key or args.value:
                parser.error("Provide both a configuration key and value.")
            else:
                show_config()

        elif args.command == "status":
            config = load_config()
            get_service_status(config)

        elif args.command == "jenkins-status":
            get_job_status()

        elif args.command == "deploy":
            trigger_deployment()

        elif args.command == "rollback":
            config = load_config()
            rollback_deployment(config)

    except (FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()