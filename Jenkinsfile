def VERSION_NUMBER = ''
def RELEASE_TYPE = ''

pipeline {
    // nice example of Jenkinsfile:
    // https://github.com/jenkinsci/pipeline-examples/blob/master/declarative-examples/jenkinsfile-examples/mavenDocker.groovy
    agent {
        dockerfile {
            // Jenkins passes .devcontainer as context. In the future
            // if anything is copied inside while creating the image
            // this might cause problems.
            dir '.devcontainer'
            label 'docker'
            args '-v /etc/passwd:/etc/passwd'
        }
    }
    environment {
        // this creates AWS_ACCESS_CREDENTIALS_USR and AWS_ACCESS_CREDENTIALS_PSW
        AWS_ACCESS_CREDENTIALS=credentials('aws_datascience_jenkins')
        // this creates DATA_SCIENCE_SALESFORCE_SANDBOX_USR and DATA_SCIENCE_SALESFORCE_SANDBOX_PSW
        DATA_SCIENCE_SALESFORCE_SANDBOX=credentials("salesforce_datascience_sandbox")
        DATA_SCIENCE_SALESFORCE_SANDBOX_CLIENT=credentials("salesforce_datascience_sandbox_client")
        DATA_SCIENCE_SALESFORCE_SANDBOX_AUTH_URL=credentials("salesforce_datascience_sandbox_auth_url")
        SLACK_BOT_API_TOKEN=credentials("slack_datascience_bi_test_bot_api_token")
    }
    parameters {
        choice(
            name: 'release_type',
            choices: ['BUGFIX OR MINOR IMPROVEMENT', 'BIG REVISION'],
            description: 'This affects the version numbering (MAJOR.MINOR). If BUGFIX OR MINOR IMPROVEMENT is selected, MINOR will be increased (this is the default option as is the first one placed in the list). If BIG REVISION is selected, MAJOR will be increased.'
        )
    }
    stages {
        stage('Testing Package') {
            steps {
                sh(script: 'pytest')
            }
        }
        stage('Bump Version'){
            when {
                branch 'develop'
            }
            steps {
                script {
                    // give execute permissions to the scripts
                    //sh(script: "chmod +x ./scripts/*.sh")

                    // Version number is in the form of MAJOR.MINOR
                    // You will often want to call .trim() on the result to strip off a trailing newline
                    // VERSION_NUMBER = sh(script: "./scripts/get_version.sh setup.py", returnStdout: true).trim()

                    // update version number depending if the release_type is
                    // "BUGFIX OR MINOR IMPROVEMENT" (increase [m]inor) or "BIG REVISION" (incr. [M]ajor)
                    if( params.release_type == 'BUGFIX OR MINOR IMPROVEMENT'){
                        RELEASE_TYPE = "minor"
                    } else {
                        RELEASE_TYPE = "major"
                    }
                    sh(script: "bump2version ${RELEASE_TYPE} --allow-dirty --verbose")
                    // NEW_VERSION = sh(script: """
                    //     bump2version ${RELEASE_TYPE} --list | sed -ne "/new_version/p" | sed -e "s/new_version=//g"
                    // """).trim()
                }
            }
        }
        stage('Merging to master and Tagging') {
            when {
                branch 'develop'
            }
            steps {
                sshagent(['bitbucket_jenkins_1704']) {
                    sh("""
                        #!/usr/bin/env bash
                        set +x
                        export GIT_SSH_COMMAND="ssh -oStrictHostKeyChecking=no"
                        git config user.name 'Jenkins CI'
                        git config user.email 'no-reply@wiris.com'
                        git push origin develop
                        git checkout -B master
                        git pull origin master
                        git merge origin/develop
                        git push origin master
                     """)
                }
            }
        }
        stage('Building Wheel') {
            when {
                branch 'develop'
            }
            steps {
                sh 'python3 setup.py bdist_wheel'
            }
        }
        stage('Copying Wheel to S3') {
            when {
                branch 'develop'
            }
            steps {
                script{
                    WHEEL_NAME = sh(script: "ls dist/santoku-*.whl", returnStdout: true).trim()
                    // // using Jenkins Ansible Plugin: we can use ansible to send it to s3
                    // // https://github.com/jenkinsci/ansible-plugin
                    // ansiblePlaybook('playbook.yml'){
                    //     extraVars: [
                    //         bucket_name: 'mybucketname',
                    //         path_in_bucket: '/my/path/in/bucket',
                    //         wheel_name: WHEEL_NAME,
                    //         region_name: 'eu-west-1'
                    //     ]
                    // }
                    // Using aws CLI
                    env.AWS_ACCESS_KEY_ID = AWS_ACCESS_CREDENTIALS_USR
                    env.AWS_SECRET_ACCESS_KEY = AWS_ACCESS_CREDENTIALS_PSW
                    env.AWS_DEFAULT_REGION = 'eu-west-1'
                    BUCKET_URI = "s3://wiris-datascience-lib/santoku/"
                    sh(script: "aws s3 cp ${WHEEL_NAME} ${BUCKET_URI}")
                }
            }
        }
    }
}
