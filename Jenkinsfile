pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'GitHub checkout successful!'
            }
        }

        stage('Docker Test') {
            steps {
                sh 'docker run --rm hello-world'
                echo 'Docker is working correctly!'
            }
        }
    }
}
