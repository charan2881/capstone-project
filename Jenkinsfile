
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
            description: 'Name of the React project'
        )
    }

    environment {
        AWS_REGION      = 'eu-north-1'
        AWS_ACCOUNT_ID  = '863555332085'
        ECR_REPOSITORY  = 'aws-deployment-capstone'
        ECS_CLUSTER     = 'aws-deployment-cluster'
        ECS_SERVICE     = 'aws-deployment-service'
        TASK_FAMILY     = 'aws-deployment-task'
        CONTAINER_NAME  = 'aws-deployment-container'
        CONTAINER_PORT  = '5000'
        ECR_URI         = '863555332085.dkr.ecr.eu-north-1.amazonaws.com/aws-deployment-capstone'
    }

    stages {

        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.PROJECT_URL?.trim()) {
                        error('PROJECT_URL is required. Run deploy-tool from your React project directory.')
                    }

                    String repoUrl = params.PROJECT_URL.trim()

                    if (!repoUrl.startsWith('https://github.com/')) {
                        error('Only HTTPS GitHub repository URLs are supported.')
                    }

                    if (repoUrl.contains(' ') ||
                        repoUrl.contains('..') ||
                        repoUrl.contains('@') ||
                        repoUrl.contains('?') ||
                        repoUrl.contains('#')) {
                        error('Invalid GitHub repository URL.')
                    }

                    echo "Repository: ${repoUrl}"
                    echo "Project: ${params.PROJECT_NAME}"
                }
            }
        }

        stage('Checkout React Project') {
            steps {
                deleteDir()

                sh '''
                    set -eu

                    echo "Cloning selected React repository..."

                    git clone --depth 1 "$PROJECT_URL" app

                    cd app

                    if [ ! -f package.json ]; then
                        echo "ERROR: package.json was not found."
                        echo "This repository does not appear to be a Node/React project."
                        exit 1
                    fi

                    echo "Repository cloned successfully."
                    echo "Project files:"
                    ls -la
                '''
            }
        }

       