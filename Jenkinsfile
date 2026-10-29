
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        string(name: 'PROJECT_URL', defaultValue: '', description: 'Public GitHub HTTPS URL of the React project')
        string(name: 'PROJECT_NAME', defaultValue: 'react-app', description: 'React project name')
    }

    environment {
        AWS_REGION     = 'eu-north-1'
        ECR_REPOSITORY = 'aws-deployment-capstone'
        ECS_CLUSTER    = 'aws-deployment-cluster'
        ECS_SERVICE    = 'aws-deployment-service'
        TASK_FAMILY    = 'aws-deployment-task'
        CONTAINER_NAME = 'aws-deployment-container'
        ECR_URI        = '863555332085.dkr.ecr.eu-north-1.amazonaws.com/aws-deployment-capstone'
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
                        echo "ERROR: package.json not found in the repository."
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
                    aws sts get-caller-identity --region "$AWS_REGION"
                '''
            }
        }

        stage('Create Docker Configuration') {
            steps {
                dir('app') {
                    sh '''
                        set -eu

                        cat > Dockerfile.deploy-tool <<'DOCKERFILE'
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
RUN chmod +x node_modules/.bin/vite && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-deploy-tool.conf /etc/nginx/conf.d/default.conf
EXPOSE 5000
CMD ["nginx", "-g", "daemon off;"]
DOCKERFILE

                        cat > nginx-deploy-tool.conf <<'NGINX'
server {
    listen 5000;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /health {
        access_log off;
        default_type text/plain;
        return 200 "healthy";
    }
}
NGINX
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                dir('app') {
                    sh '''
                        set -eu

                        COMMIT_SHA=$(git rev-parse --short=12 HEAD)
                        IMAGE_TAG="${BUILD_NUMBER}-${COMMIT_SHA}"
                        echo "$IMAGE_TAG" > ../image-tag.txt

                        docker build \
                            -f Dockerfile.deploy-tool \
                            -t "$ECR_URI:$IMAGE_TAG" \
                            -t "$ECR_URI:latest" \
                            .
                    '''
                }
            }
        }

        stage('Login to ECR') {
            steps {
                sh '''
                    set -eu
                    aws ecr get-login-password --region "$AWS_REGION" |
                        docker login --username AWS --password-stdin "$ECR_URI"
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
                        --output json > task-definition-current.json

                    export NEW_IMAGE="$ECR_URI:$(cat image-tag.txt)"
                    export EXPECTED_CONTAINER="$CONTAINER_NAME"

                    python3 - <<'PY'
import json
import os

with open("task-definition-current.json", encoding="utf-8") as f:
    task = json.load(f)

for key in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
    "deregisteredAt", "deregisteredBy"
):
    task.pop(key, None)

expected = os.environ["EXPECTED_CONTAINER"]
image = os.environ["NEW_IMAGE"]
found = False

for container in task.get("containerDefinitions", []):
    if container.get("name") == expected:
        container["image"] = image
        found = True

if not found:
    raise SystemExit(f"Container '{expected}' not found in task definition.")

with open("task-definition-new.json", "w", encoding="utf-8") as f:
    json.dump(task, f, indent=2)

print("Task definition prepared with image:", image)
PY
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
                        --output text > task-definition-arn.txt

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
                        --output table
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: React application deployed to ECS.'
        }

        failure {
            echo 'FAILED: Check the first failing stage in the Jenkins Console Output.'
        }

        always {
            echo 'Deployment pipeline finished.'
        }
    }
}