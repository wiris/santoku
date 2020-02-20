pipeline {
    agent {
        label 'sre'
    }
    environment {
        AWS_ACCESS_KEY_ID=credential('super-secret-credential')
    }
    stages {
        stage('build-wheel') {
            agent {
                dockerfile {
                    dir '.devcontainer'
                    label 'docker'
                }
            }
            steps {
                sh 'echo $AWS_ACCESS_KEY_ID'
                //sh 'python3 setup.py bdist_wheel'
            }
        }
    }
}
