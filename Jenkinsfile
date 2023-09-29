pipeline {
    agent any
    environment {
        DATE_TAG = sh(returnStdout: true, script: 'date +%Y-%m%d-%H%M').trim()
        IMAGE_NAME = "192.168.8.66:5000/ai-connector
    }
    stages {
        stage('Build') {
            steps {
                sh "docker build -t $IMAGE_NAME:latest -t $IMAGE_NAME:$DATE_TAG . --build-arg NOW=$DATE_TAG"
            }
        }
        stage('Deploy') {
            steps {
                sh '''
                    docker push $IMAGE_NAME:latest
                    docker push $IMAGE_NAME:$DATE_TAG
                '''
            }
        }
    }
}
