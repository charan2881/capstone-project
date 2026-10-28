```groovy
pipeline {
    agent any

    environment {
        AWS_REGION = 'eu-north-1'
        AWS_ACCOUNT_ID = '863555332085'
        ECR_REPOSITORY = 'aws-deployment-capstone'
        ECS_CLUSTER = 'aws-deployment-cluster'
        ECS_SERVICE = 'aws-deployment-service'
        TASK_FAMILY = 'aws-deployment-task'
        CONTAINER_NAME = 'aws-deployment-container'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'Source code checked out successfully.'
            }
        }

        stage('Check Environment') {
            steps {
                sh '''
                    git --version
                    docker --version
                    aws --version
                    aws sts get-caller-identity
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                }

                sh '''
                    ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

                    docker build \
                        -t "${ECR_URI}:${IMAGE_TAG}" \
                        -t "${ECR_URI}:latest" .
                '''
            }
        }

        stage('Login to Amazon ECR') {
            steps {
                sh '''
                    aws ecr get-login-password --region "$AWS_REGION" |
                    docker login \
                        --username AWS \
                        --password-stdin \
                        "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                '''
            }
        }

        stage('Push Image to ECR') {
            steps {
                sh '''
                    ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

                    docker push "${ECR_URI}:${IMAGE_TAG}"
                    docker push "${ECR_URI}:latest"
                '''
            }
        }

        stage('Prepare ECS Task Definition') {
            steps {
                sh '''
                    ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

                    aws ecs describe-task-definition \
                        --task-definition "$TASK_FAMILY" \
                        --region "$AWS_REGION" \
                        --query 'taskDefinition' \
                        --output json \
                        --no-cli-pager > task-definition-current.json

                    python3 - <<'PY'
import json
import os

with open("task-definition-current.json", "r") as f:
    task = json.load(f)

# Remove fields AWS generates and does not accept when registering a revision.
for field in [
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "deregisteredAt",
]:
    task.pop(field, None)

expected_container = os.environ["CONTAINER_NAME"]
image_uri = (
    f'{os.environ["AWS_ACCOUNT_ID"]}.dkr.ecr.'
    f'{os.environ["AWS_REGION"]}.amazonaws.com/'
    f'{os.environ["ECR_REPOSITORY"]}:{os.environ["IMAGE_TAG"]}'
)

found = False

for container in task["containerDefinitions"]:
    if container["name"] == expected_container:
        container["image"] = image_uri
        found = True

if not found:
    raise SystemExit(
        f"ERROR: Container '{expected_container}' was not found "
        "in the current task definition."
    )

with open("task-definition-new.json", "w") as f:
    json.dump(task, f, indent=2)

print(f"Prepared task definition using image: {image_uri}")
PY
                '''
            }
        }

        stage('Register ECS Task Definition') {
            steps {
                script {
                    env.TASK_DEFINITION_ARN = sh(
                        script: '''
                            aws ecs register-task-definition \
                                --cli-input-json file://task-definition-new.json \
                                --region "$AWS_REGION" \
                                --query 'taskDefinition.taskDefinitionArn' \
                                --output text \
                                --no-cli-pager
                        ''',
                        returnStdout: true
                    ).trim()
                }

                echo "Registered task definition: ${env.TASK_DEFINITION_ARN}"
            }
        }

        stage('Deploy to ECS') {
            steps {
                sh '''
                    aws ecs update-service \
                        --cluster "$ECS_CLUSTER" \
                        --service "$ECS_SERVICE" \
                        --task-definition "$TASK_DEFINITION_ARN" \
                        --region "$AWS_REGION" \
                        --no-cli-pager

                    echo "Waiting for ECS deployment to stabilize..."

                    aws ecs wait services-stable \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION"

                    echo "ECS deployment completed successfully."
                '''
            }
        }

        stage('Verify ECS Deployment') {
            steps {
                sh '''
                    aws ecs describe-services \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION" \
                        --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,TaskDefinition:taskDefinition}' \
                        --output json \
                        --no-cli-pager
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Image built, pushed to ECR, and deployed to ECS!'
        }

        failure {
            echo 'FAILED: Check Jenkins Console Output for the failing stage.'
        }
    }
}
```
