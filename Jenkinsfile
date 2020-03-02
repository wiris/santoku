def VERSION_NUMBER = ''

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
        stage('Testing Package') {
            steps {
                sh(script: 'echo nose2')
            }
        }
        stage('Update version number'){
            steps {
                script {
                    // update version number
                    VERSION_NUMBER = sh(script: 'echo 0.0.1', returnStdout: true)
                }
            }
        }
        stage('Merge to master & Tag') {
            steps {
                // script {
                //     // sshagent(credentials: ['bitbucket_jenkins_1704']) {
                //     //     git branch: 'master', url: 'git@bitbucket.org:wiris/plugins.git';
                //     //     sh(script: 'git fetch --all');
                //     //     sh(script: 'git checkout master');
                //     //     sh(script: 'git merge origin/develop --ff-only');
                //     //     sh(script: 'git push origin master');
                //     //     sh(script: 'git tag ${VERSION_NUMBER}')
                //     // }
                //     sh(script: 'echo git tag ${VERSION_NUMBER}')
                // }
                echo "git tag ${VERSION_NUMBER}"
            }
        }
        stage('Wheel building') {
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
        stage('Wheel orchestration to S3') {
            steps {
                sh 'echo "#TODO: Implement sending wheel to S3 with ansible"'
                // instead of creating a python3 script we can use ansible to send it to s3
                // https://github.com/jenkinsci/ansible-plugin
            }
        }
    }
}
