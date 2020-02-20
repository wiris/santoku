pipeline {
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
        stage('build-wheel') {
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
    }
}
