
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
            description: 'React project name'
        )
    }

    environment {
        AWS_REGION     = 'ap-south-1'
        AWS_ACCOUNT_ID = '587748224398'

        ECR_REPOSITORY = 'react-deployment-app'
        ECR_URI        = '587748224398.dkr.ecr.ap-south-1.amazonaws.com/react-deployment-app'

        ECS_CLUSTER    = 'react-deployment-cluster'
        ECS_SERVICE    = 'react-deployment-service'
        TASK_FAMILY    = 'react-deployment-task'
        CONTAINER_NAME = 'react-app'

        CONTAINER_PORT = '5000'
    }

    stages {

        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.PROJECT_URL?.trim()) {
                        error('PROJECT_URL is required.')
                    }

                    if (!params.PROJECT_URL.startsWith('https://github.com/')) {
                        error('Provide a valid HTTPS GitHub repository URL.')
                    }

                    if (!params.PROJECT_NAME?.trim()) {
                        error('PROJECT_NAME is required.')
                    }

                    echo "Project: ${params.PROJECT_NAME}"
                    echo "Repository: ${params.PROJECT_URL}"
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

        stage('Check Environment') {
            steps {
                sh '''
                    set -eu

                    git --version
                    docker --version
                    aws --version

                    ACTUAL_ACCOUNT=$(aws sts get-caller-identity \
                        --query Account \
                        --output text)

                    echo "AWS Account: $ACTUAL_ACCOUNT"

                    if [ "$ACTUAL_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
                        echo "ERROR: Incorrect AWS account."
                        exit 1
                    fi

                    aws ecr describe-repositories \
                        --repository-names "$ECR_REPOSITORY" \
                        --region "$AWS_REGION"

                    echo "AWS environment verified."
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
'    listen 5000;' \
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

EXPOSE 5000

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
                    echo "Image tag: $IMAGE_TAG"
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

                    echo "Docker image pushed successfully."
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
                        > task-definition-current.json

                    export NEW_IMAGE="$ECR_URI:$(cat image-tag.txt)"

                    export EXPECTED_CONTAINER="$CONTAINER_NAME"

                    export EXPECTED_PORT="$CONTAINER_PORT"

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

expected_container = os.environ["EXPECTED_CONTAINER"]
expected_port = int(os.environ["EXPECTED_PORT"])
new_image = os.environ["NEW_IMAGE"]

found = False

for container in task.get("containerDefinitions", []):
    if container.get("name") == expected_container:
        container["image"] = new_image
        found = True

        ports = container.get("portMappings", [])

        if not any(
            p.get("containerPort") == expected_port
            for p in ports
        ):
            raise SystemExit(
                f"ERROR: Container port {expected_port} "
                "is not configured in the ECS task definition."
            )

if not found:
    raise SystemExit(
        f"ERROR: Container '{expected_container}' not found."
    )

with open("task-definition-new.json", "w", encoding="utf-8") as f:
    json.dump(task, f, indent=2)

print("Updated image:", new_image)
print("Container:", expected_container)
print("Container port:", expected_port)
PY

                    echo "Task definition prepared."
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
                        > task-definition-arn.txt

                    echo "Registered task definition:"
                    cat task-definition-arn.txt
                '''
            }
        }

        stage('Deploy to ECS') {
            steps {
                sh '''
                    set -eu

                    TASK_DEFINITION_ARN=$(cat task-definition-arn.txt)

                    aws ecs update-service \
                        --cluster "$ECS_CLUSTER" \
                        --service "$ECS_SERVICE" \
                        --task-definition "$TASK_DEFINITION_ARN" \
                        --region "$AWS_REGION"

                    echo "Waiting for ECS service stability..."

                    aws ecs wait services-stable \
                        --cluster "$ECS_CLUSTER" \
                        --service "$ECS_SERVICE" \
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
                        --output table

                    echo "React deployment verification completed."
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: React application deployed to AWS ECS.'
        }

        failure {
            echo 'FAILED: Check the first failing stage in Jenkins Console Output.'
        }

        always {
            echo 'Deployment pipeline finished.'
        }
    }
}
