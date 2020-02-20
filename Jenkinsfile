pipeline {
    agent {
        label 'sre'
    }
    environment {
        AWS_ACCESS_KEY_ID=credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY=credentials('AWS_SECRET_ACCESS_KEY')
    }
    stages {
        stage('build-wheel') {
            agent {
                dockerfile {
                    // Jenkins passes .devcontainer as context. In the future
                    // if anything is copied inside while creating the image
                    // this might cause problems
                    dir '.devcontainer'
                    label 'docker'
                }
            }
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
    }
}
