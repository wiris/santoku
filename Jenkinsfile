pipeline {
    // nice example of Jenkinsfile:
    // https://github.com/jenkinsci/pipeline-examples/blob/master/declarative-examples/jenkinsfile-examples/mavenDocker.groovy

    //agent {
    //    label 'sre'
    //}
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
        AWS_ACCESS_KEY_ID=credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY=credentials('AWS_SECRET_ACCESS_KEY')
    }
    stages {
        stage('build') {
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
        stage('test') {
            steps {
                sh 'nose2'
            }
        }
        stage('cool-name') {
            steps {
                sh 'pip install santoku-*.py'
                // instead of creating a python3 script we can use ansible to send it to s3
                // https://github.com/jenkinsci/ansible-plugin
                sh 'python3 script/move_to_s3.py'
            }
        }
    }
}
