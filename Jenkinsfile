pipeline {
    // nice example of Jenkinsfile:
    // https://github.com/jenkinsci/pipeline-examples/blob/master/declarative-examples/jenkinsfile-examples/mavenDocker.groovy
    agent {
        dockerfile {
            // Jenkins passes .devcontainer as context. In the future
            // if anything is copied inside while creating the image
            // this might cause problems
            dir '.devcontainer'
            label 'docker'
        }
    }
    environment {
        // this creates AWS_ACCESS_CREDENTIALS_USR and AWS_ACCESS_CREDENTIALS_PSW
        AWS_ACCESS_CREDENTIALS=credentials('aws_datascience_admin')
    }
    stages {
        stage('test') {
            steps {
                sh 'nose2'
            }
        }
        stage('wheel-build') {
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
        stage('wheel-orchestration') {
            steps {
                sh 'echo "#TODO: Implement sending wheel to S3 with ansible"'
                // instead of creating a python3 script we can use ansible to send it to s3
                // https://github.com/jenkinsci/ansible-plugin
            }
        }
    }
}
