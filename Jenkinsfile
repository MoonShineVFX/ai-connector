pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh "docker build -t 192.168.8.66:5000/ai-connector . --build-arg NOW=\$(date +%Y-%m%d-%H%M)"
            }
        }
        stage('Deploy') {
            steps {
                sh "docker push 192.168.8.66:5000/ai-connector"
            }
        }
    }
}
