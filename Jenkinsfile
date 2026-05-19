pipeline {
    agent any

    stages {

        stage('Clone') {
            steps {
                git branch: 'main',
                url: 'https://github.com/hassan-maher-dev/Land-Cover-Classification.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t remote-sensing-app .'
            }
        }

        stage('Stop Old Container') {
            steps {
                sh '''
                docker stop remote-sensing-container || true
                docker rm remote-sensing-container || true
                '''
            }
        }

        stage('Run New Container') {
            steps {
                sh '''
                docker run -d \
                --name remote-sensing-container \
                --restart always \
                -p 5000:5000 \
                -v /opt/remote-sensing/uploads:/app/uploads \
                -v /opt/remote-sensing/Outputs:/app/Outputs \
                remote-sensing-app
                '''
            }
        }

        stage('Cleanup') {
            steps {
                sh 'docker image prune -f'
            }
        }

    }

    post {
        success {
            echo 'Deployment Successful 🚀'
        }

        failure {
            echo 'Deployment Failed ❌'
        }
    }
}