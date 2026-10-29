
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        string(
            name: 'PROJECT_URL',
            defaultValue: '',
            description: 'HTTPS Git repository URL of the React project'
        )

        string(
            name: 'PROJECT_NAME',
            defaultValue: 'react-app',
            description: 'Name of the React project'
        )
    }

    environment {
        AWS_REGION       = 'eu-north-1'
        AWS_ACCOUNT_ID   = '863555332085'
        ECR_REPOSITORY   = 'aws-deployment-capstone'
        ECS_CLUSTER      = 'aws-deployment-cluster'
        ECS_SERVICE      = 'aws-deployment-service'
        TASK_FAMILY      = 'aws-deployment-task'
        CONTAINER_NAME   = 'aws-deployment-container'
        CONTAINER_PORT   = '5000'
        ECR_URI          = '863555332085.dkr.ecr.eu-north-1.amazonaws.com/aws-deployment-capstone'
    }

    stages {

        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.PROJECT_URL?.trim()) {
                        error(
                            'PROJECT_URL is required. Run deploy-tool deploy ' +
                            'from a Git repository with an origin remote.'
                        )
                    }

                    if (!(params.PROJECT_URL ==~
                        /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+(?:\.git)?\/?$/)) {
                        error(
                            'PROJECT_URL must be a public GitHub HTTPS repository URL.'
                        )
                    }
                }

                echo "Project: ${params.PROJECT_NAME}"
                echo "Repository: ${params.PROJECT_URL}"
            }
        }

        stage('Checkout Selected React Project') {
            steps {
                deleteDir()

                sh '''
                    set -eu

                    echo "Cloning the requested repository..."

                    git clone --depth 1 "$PROJECT_URL" .

                    echo "Repository checked out:"
                    git remote get-url origin

                    echo "Latest commit:"
                    git log -1 --oneline

                    echo "Checking for package.json..."

                    if [ ! -f package.json ]; then
                        echo "ERROR: package.json was not found."
                        echo "This repository does not appear to be a Node.js project."
                        exit 1
                    fi
                '''
            }
        }

        stage('Check Environment') {
            steps {
                sh '''
                    set -eu

                    git --version
                    docker --version
                    aws --version
                    node --version || true

                    aws sts get-caller-identity \
                        --region "$AWS_REGION" \
                        --no-cli-pager
                '''
            }
        }

        stage('Prepare React Dockerfile') {
            steps {
                script {
                    writeFile(
                        file: 'Dockerfile.deploy-tool',
                        text: '''FROM node:22-alpine AS build

WORKDIR /app

COPY . .

RUN set -eux; \\
    if [ -f package-lock.json ]; then \\
        npm ci; \\
    elif [ -f pnpm-lock.yaml ]; then \\
        corepack enable; \\
        pnpm install --frozen-lockfile; \\
    elif [ -f yarn.lock ]; then \\
        corepack enable; \\
        yarn install --frozen-lockfile; \\
    else \\
        npm install; \\
    fi; \\
    if [ -f pnpm-lock.yaml ]; then \\
        pnpm run build; \\
    elif [ -f yarn.lock ]; then \\
        yarn build; \\
    else \\
        npm run build; \\
    fi; \\
    if [ -d dist ]; then \\
        mv dist /app/site; \\
    elif [ -d build ]; then \\
        mv build /app/site; \\
    else \\
        echo "ERROR: No dist/ or build/ directory was produced."; \\
        exit 1; \\
    fi

FROM nginx:alpine

COPY nginx-deploy-tool.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/site /usr/share/nginx/html

EXPOSE 5000

CMD ["nginx", "-g", "daemon off;"]
'''
                    )

                    writeFile(
                        file: 'nginx-deploy-tool.conf',
                        text: '''server {
    listen 5000;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
'''
                    )
                }
            }
        }

        stage('Build React Application and Docker Image') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()

                    env.IMAGE_URI = "${env.ECR_URI}:${env.IMAGE_TAG}"
                }

                sh '''
                    set -eu

                    echo "Building project: $PROJECT_NAME"
                    echo "Image: $IMAGE_URI"

                    docker build \
                        --pull \
                        -f Dockerfile.deploy-tool \
                        -t "$IMAGE_URI" \
                        -t "$ECR_URI:latest" \
                        .

                    docker image inspect "$IMAGE_URI" >/dev/null
                '''
            }
        }

        stage('Login to Amazon ECR') {
            steps {
                sh '''
                    set -eu

                    aws ecr get-login-password \
                        --region "$AWS_REGION" \
                    | docker login \
                        --username AWS \
                        --password-stdin "$ECR_URI"
                '''
            }
        }

        stage('Push Docker Image to ECR') {
            steps {
                sh '''
                    set -eu

                    docker push "$IMAGE_URI"
                    docker push "$ECR_URI:latest"
                '''
            }
        }

        stage('Prepare ECS Task Definition') {
            steps {
                sh '''
                    set -eu

                    aws ecs describe-task-definition \
                        --task-definition "$TASK_FAMILY" \
                        --region "$AWS_REGION" \
                        --query taskDefinition \
                        --output json \
                        --no-cli-pager \
                        > task-definition-current.json

                    python3 - <<'PY'
import json
import os
import sys

with open("task-definition-current.json", encoding="utf-8") as file:
    task = json.load(file)

# Remove AWS-generated fields that cannot be supplied when registering
# a new task-definition revision.
for key in (
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "deregisteredAt",
):
    task.pop(key, None)

container_name = os.environ["CONTAINER_NAME"]
image_uri = os.environ["IMAGE_URI"]

containers = task.get("containerDefinitions", [])

target = next(
    (container for container in containers
     if container.get("name") == container_name),
    None,
)

if target is None:
    available = [c.get("name") for c in containers]
    sys.exit(
        f"Container '{container_name}' was not found. "
        f"Available containers: {available}"
    )

target["image"] = image_uri

# Keep the existing task definition's port mappings, execution role,
# task role, CPU, memory, and logging configuration.
with open("task-definition-new.json", "w", encoding="utf-8") as file:
    json.dump(task, file, indent=2)

print(f"Container: {container_name}")
print(f"New image: {image_uri}")
PY
                '''
            }
        }

        stage('Register ECS Task Definition') {
            steps {
                script {
                    env.NEW_TASK_DEFINITION_ARN = sh(
                        script: '''
                            aws ecs register-task-definition \
                                --cli-input-json file://task-definition-new.json \
                                --region "$AWS_REGION" \
                                --query taskDefinition.taskDefinitionArn \
                                --output text \
                                --no-cli-pager
                        ''',
                        returnStdout: true
                    ).trim()
                }

                echo "Registered task definition: ${env.NEW_TASK_DEFINITION_ARN}"
            }
        }

        stage('Deploy to ECS') {
            steps {
                sh '''
                    set -eu

                    echo "Updating ECS service..."

                    aws ecs update-service \
                        --cluster "$ECS_CLUSTER" \
                        --service "$ECS_SERVICE" \
                        --task-definition "$NEW_TASK_DEFINITION_ARN" \
                        --region "$AWS_REGION" \
                        --no-cli-pager

                    echo "Waiting for ECS deployment to stabilize..."

                    aws ecs wait services-stable \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION"
                '''
            }
        }

        stage('Verify ECS Deployment') {
            steps {
                sh '''
                    set -eu

                    aws ecs describe-services \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION" \
                        --query 'services[0].{
                            Service:serviceName,
                            Status:status,
                            Desired:desiredCount,
                            Running:runningCount,
                            Pending:pendingCount,
                            TaskDefinition:taskDefinition
                        }' \
                        --output table \
                        --no-cli-pager
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: React application deployed to ECS.'
            echo "Project: ${params.PROJECT_NAME}"
            echo "Repository: ${params.PROJECT_URL}"
            echo "Image: ${env.IMAGE_URI}"
        }

        failure {
            echo 'FAILED: Check the first failed stage in Console Output.'
            echo 'If ECS did not stabilize, inspect ECS service events and target health.'
        }

        always {
            echo 'Deployment pipeline finished.'
        }
    }
}
