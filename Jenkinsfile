def VERSION_NUMBER = ''
def RELEASE_TYPE = ''

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
        stage('Updating Version Number'){
            when {
                branch 'develop'
            }
            steps {
                script {
                    // give execute permissions to the scripts
                    sh(script: "chmod +x ./scripts/*.sh")

                    // Version number is in the form of MAJOR.MINOR
                    // You will often want to call .trim() on the result to strip off a trailing newline
                    VERSION_NUMBER = sh(script: "./scripts/get_version.sh setup.py", returnStdout: true).trim()

                    // update version number depending if the release_type is
                    // "BUGFIX OR MINOR IMPROVEMENT" (increase [m]inor) or "BIG REVISION" (incr. [M]ajor)
                    if( params.release_type == 'BUGFIX OR MINOR IMPROVEMENT'){
                        RELEASE_TYPE = "m"
                    } else {
                        RELEASE_TYPE = "M"
                    }
                    VERSION_NUMBER = sh(script: "./scripts/increase_version.sh ${VERSION_NUMBER} ${RELEASE_TYPE}", returnStdout: true).trim()
                    sh(script: "./scripts/set_version.sh setup.py ${VERSION_NUMBER}")
                }
            }
        }
        stage('Merging to master & Tagging') {
            when {
                branch 'develop'
            }
            steps {
                sshagent(credentials: ['bitbucket_jenkins_1704']) {
                    //git branch: 'master', url: 'git@bitbucket.org:wiris/etl.python.toolkit.git', credentialsId: 'bitbucket_jenkins_1704'
                    //sh(script: 'git fetch --all')
                    sh(script: 'git checkout develop')
                    // sh(script: 'git add setup.py')
                    // sh(script: 'git commit -m "Bump version"')
                    // sh(script: 'git push origin develop')
                    // sh(script: 'git checkout master')
                    // sh(script: 'git merge origin/develop --ff-only')
                    // sh(script: 'git push origin master')
                    // sh(script: "git tag ${VERSION_NUMBER}")
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
                    WHEEL_NAME = sh(script: "ls dist/Santoku-*.whl", returnStdout: true).trim()
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
                    BUCKET_URL = "s3://my-bucket/my/path/in/bucket"
                    // move this up to environmetn section
                    env.AWS_ACCESS_KEY_ID = AWS_ACCESS_CREDENTIALS_USR
                    env.AWS_SECRET_ACCESS_KEY = AWS_ACCESS_CREDENTIALS_PSW
                    env.AWS_DEFAULT_REGION = 'eu-west-1'
                    sh(script: "echo aws s3 cp ${WHEEL_NAME} ${BUCKET_URL}")
                }
            }
        }
    }
}
