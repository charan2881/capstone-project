pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'GitHub checkout successful!'
            }
        }

        stage('Check Environment') {
            steps {
                sh 'git --version'
                sh 'docker --version'
            }
        }
    }
}
