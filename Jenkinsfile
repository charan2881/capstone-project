
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
            description: 'Public GitHub HTTPS URL of the React project'
        )

        string(
            name: 'PROJECT_NAME',
            defaultValue: 'react-app',
            description: 'Unique project name using lowercase letters, numbers and hyphens'
        )
    }

    environment {
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '587748224398'

        ECS_CLUSTER = 'react-deployment-cluster'
        BASE_TASK_FAMILY = 'react-deployment-task'

        CONTAINER_PORT = '80'
    }

    stages {

        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.PROJECT_URL?.trim()) {
                        error('PROJECT_URL is required.')
                    }

                    if (!(params.PROJECT_URL ==~ /^https:\/\/github\.com\/[^\/]+\/[^\/]+(?:\.git)?\/?$/)) {
                        error('Provide a valid GitHub HTTPS repository URL.')
                    }

                    def projectName = params.PROJECT_NAME?.trim()

                    if (!projectName || !(projectName ==~ /^[a-z0-9]+(?:-[a-z0-9]+)*$/)) {
                        error('PROJECT_NAME must use lowercase letters, numbers and single hyphens.')
                    }

                    if (projectName.length() > 40) {
                        error('PROJECT_NAME must not exceed 40 characters.')
                    }

                    env.PROJECT_NAME = projectName
                    env.ECR_REPOSITORY = projectName
                    env.ECR_URI = "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com/${projectName}"
                    env.ECS_SERVICE = "${projectName}-service"
                    env.TASK_FAMILY = "${projectName}-task"
                    env.CONTAINER_NAME = projectName
                    env.LOG_GROUP = "/ecs/${projectName}-task"

                    echo "Project: ${projectName}"
                    echo "Repository: ${params.PROJECT_URL}"
                    echo "ECR: ${env.ECR_REPOSITORY}"
                    echo "ECS service: ${env.ECS_SERVICE}"
                    echo "Task family: ${env.TASK_FAMILY}"
                }
            }
        }

        stage('Checkout React Project') {
            steps {
                deleteDir()

                sh '''
                    set -eu

                    git clone --depth 1 "$PROJECT_URL" app

                    if [ ! -f app/package.json ]; then
                        echo "ERROR: package.json not found."
                        exit 1
                    fi

                    echo "React project cloned successfully."
                '''
            }
        }

        stage('Check Environment and Create Resources') {
            steps {
                sh '''
                    set -eu

                    git --version
                    docker --version
                    aws --version

                    ACTUAL_ACCOUNT=$(aws sts get-caller-identity \
                        --query Account --output text)

                    if [ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
                        echo "ERROR: Incorrect AWS account."
                        exit 1
                    fi

                    echo "Checking ECR repository: $ECR_REPOSITORY"

                    if ! aws ecr describe-repositories \
                        --repository-names "$ECR_REPOSITORY" \
                        --region "$AWS_REGION" \
                        --no-cli-pager >/dev/null 2>&1; then

                        aws ecr create-repository \
                            --repository-name "$ECR_REPOSITORY" \
                            --image-scanning-configuration scanOnPush=true \
                            --region "$AWS_REGION" \
                            --no-cli-pager
                    fi

                    echo "Checking CloudWatch log group: $LOG_GROUP"

                    LOG_GROUP_EXISTS=$(aws logs describe-log-groups \
                        --log-group-name-prefix "$LOG_GROUP" \
                        --region "$AWS_REGION" \
                        --query "logGroups[?logGroupName=='$LOG_GROUP'] | length(@)" \
                        --output text)

                    if [ "$LOG_GROUP_EXISTS" = "0" ]; then
                        aws logs create-log-group \
                            --log-group-name "$LOG_GROUP" \
                            --region "$AWS_REGION" \
                            --no-cli-pager
                    fi

                    echo "AWS resources checked successfully."
                '''
            }
        }

        stage('Create Docker Configuration') {
            steps {
                sh '''
                    set -eu

                    cat > Dockerfile.deploy-tool <<'DOCKERFILE'
FROM node:22-alpine AS build

WORKDIR /app

COPY app/package*.json ./

RUN if [ -f package-lock.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi

COPY app/ ./

RUN npm run build && \
    mkdir -p /output && \
    if [ -d dist ]; then \
        cp -R dist/. /output/; \
    elif [ -d build ]; then \
        cp -R build/. /output/; \
    else \
        echo "ERROR: React build output not found."; \
        exit 1; \
    fi

FROM nginx:alpine

COPY --from=build /output/ /usr/share/nginx/html/

RUN printf '%s\\n' \
'server {' \
'    listen 80;' \
'    server_name _;' \
'    root /usr/share/nginx/html;' \
'    index index.html;' \
'    location / {' \
'        try_files $uri $uri/ /index.html;' \
'    }' \
'    location /health {' \
'        access_log off;' \
'        default_type text/plain;' \
'        return 200 "healthy";' \
'    }' \
'}' \
> /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
DOCKERFILE

                    echo "Docker configuration created."
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu

                    COMMIT_SHA=$(git -C app rev-parse --short=12 HEAD)
                    IMAGE_TAG="${BUILD_NUMBER}-${COMMIT_SHA}"

                    echo "$IMAGE_TAG" > image-tag.txt

                    docker build \
                        -f Dockerfile.deploy-tool \
                        -t "$ECR_URI:$IMAGE_TAG" \
                        -t "$ECR_URI:latest" \
                        .

                    echo "Docker image built successfully."
                    echo "Image: $ECR_URI:$IMAGE_TAG"
                '''
            }
        }

        stage('Login to Amazon ECR') {
            steps {
                sh '''
                    set -eu

                    ECR_REGISTRY="${ECR_URI%%/*}"

                    aws ecr get-login-password \
                        --region "$AWS_REGION" |
                        docker login \
                        --username AWS \
                        --password-stdin "$ECR_REGISTRY"

                    echo "ECR login successful."
                '''
            }
        }

        stage('Push Docker Image') {
            steps {
                sh '''
                    set -eu

                    IMAGE_TAG=$(cat image-tag.txt)

                    docker push "$ECR_URI:$IMAGE_TAG"
                    docker push "$ECR_URI:latest"

                    echo "Image pushed to $ECR_REPOSITORY."
                '''
            }
        }

        stage('Prepare ECS Task Definition') {
            steps {
                sh '''
                    set -eu

                    aws ecs describe-task-definition \
                        --task-definition "$BASE_TASK_FAMILY" \
                        --region "$AWS_REGION" \
                        --query taskDefinition \
                        --output json \
                        --no-cli-pager > task-definition-current.json

                    export NEW_IMAGE="$ECR_URI:$(cat image-tag.txt)"

                    python3 - <<'PY'
import json
import os

with open("task-definition-current.json", encoding="utf-8") as f:
    task = json.load(f)

remove_keys = [
    "taskDefinitionArn",
    "revision",
    "status",
    "requiresAttributes",
    "compatibilities",
    "registeredAt",
    "registeredBy",
    "deregisteredAt",
    "deregisteredBy"
]

for key in remove_keys:
    task.pop(key, None)

project = os.environ["PROJECT_NAME"]
image = os.environ["NEW_IMAGE"]
log_group = os.environ["LOG_GROUP"]
region = os.environ["AWS_REGION"]

task["family"] = f"{project}-task"

containers = task.get("containerDefinitions", [])

if not containers:
    raise SystemExit("ERROR: Base task definition has no containers.")

container = containers[0]
container["name"] = project
container["image"] = image

ports = container.get("portMappings", [])

if not any(p.get("containerPort") == 80 for p in ports):
    raise SystemExit("ERROR: Base task definition does not expose port 80.")

container["logConfiguration"] = {
    "logDriver": "awslogs",
    "options": {
        "awslogs-group": log_group,
        "awslogs-region": region,
        "awslogs-stream-prefix": project
    }
}

with open("task-definition-new.json", "w", encoding="utf-8") as f:
    json.dump(task, f, indent=2)

print("Task family:", task["family"])
print("Container:", project)
print("Image:", image)
print("Log group:", log_group)
PY

                    echo "Project-specific task definition prepared."
                '''
            }
        }

        stage('Register ECS Task Definition') {
            steps {
                sh '''
                    set -eu

                    aws ecs register-task-definition \
                        --cli-input-json file://task-definition-new.json \
                        --region "$AWS_REGION" \
                        --query taskDefinition.taskDefinitionArn \
                        --output text \
                        --no-cli-pager > task-definition-arn.txt

                    echo "Registered task definition:"
                    cat task-definition-arn.txt
                '''
            }
        }

        stage('Create or Update ECS Service') {
            steps {
                sh '''
                    set -eu

                    TASK_DEFINITION_ARN=$(cat task-definition-arn.txt)

                    SERVICE_STATUS=$(aws ecs describe-services \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION" \
                        --query 'services[0].status' \
                        --output text \
                        --no-cli-pager)

                    if [ "$SERVICE_STATUS" = "ACTIVE" ]; then

                        echo "Updating existing service: $ECS_SERVICE"

                        aws ecs update-service \
                            --cluster "$ECS_CLUSTER" \
                            --service "$ECS_SERVICE" \
                            --task-definition "$TASK_DEFINITION_ARN" \
                            --region "$AWS_REGION" \
                            --no-cli-pager

                    else

                        echo "Creating new service: $ECS_SERVICE"

                        aws ecs create-service \
                            --cluster "$ECS_CLUSTER" \
                            --service-name "$ECS_SERVICE" \
                            --task-definition "$TASK_DEFINITION_ARN" \
                            --desired-count 1 \
                            --launch-type FARGATE \
                            --network-configuration "awsvpcConfiguration={subnets=[subnet-0b56f981664920282,subnet-04af69f44a5b07a8e,subnet-0676b4c58d23e643b],securityGroups=[sg-044bca5aafeec830f],assignPublicIp=ENABLED}" \
                            --region "$AWS_REGION" \
                            --no-cli-pager
                    fi

                    echo "Waiting for ECS service stability..."

                    aws ecs wait services-stable \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION"

                    echo "ECS service is stable."
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    set -eu

                    aws ecs describe-services \
                        --cluster "$ECS_CLUSTER" \
                        --services "$ECS_SERVICE" \
                        --region "$AWS_REGION" \
                        --query 'services[0].{Status:status,Desired:desiredCount,Running:runningCount,TaskDefinition:taskDefinition}' \
                        --output table \
                        --no-cli-pager

                    echo "Deployment verification completed."
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Project deployed to its own AWS ECS service.'
        }

        failure {
            echo 'FAILED: Check the first failing stage in Jenkins Console Output.'
        }

        always {
            echo 'Deployment pipeline finished.'
        }
    }
}
