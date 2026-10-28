pipeline {
    agent any

    environment {
        AWS_REGION = 'eu-north-1'
        AWS_ACCOUNT_ID = '863555332085'
        ECR_REPOSITORY = 'aws-deployment-capstone'
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
    }

    post {
        success {
            echo 'SUCCESS: Docker image built and pushed to Amazon ECR!'
        }

        failure {
            echo 'FAILED: Check the Jenkins Console Output for the error.'
        }
    }
}
