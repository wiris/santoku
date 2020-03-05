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
        parameters {
            choice(
                name: 'release_type',
                choices: ['BUGFIX OR MINOR IMPROVEMENT', 'BIG REVISION'],
                description: """This affects the version numbering (MAJOR.MINOR).
                              If "BUGFIX OR MINOR IMPROVEMENT" is selected, MINOR will be increased
                              (this is the default option as is the first one placed in the list).
                              If "BIG REVISION" is selected, MAJOR will be increased."""
            )
        }
    }
    stages {
        stage('Testing Package') {
            steps {
                sh(script: 'pytest')
            }
        }
        stage('Updating Minor Version Number'){
            when {
                branch 'develop'
            }
            steps {
                script {
                    // Version number is in the form of MAJOR.MINOR
                    VERSION_NUMBER = sh(script: "grep version setup.py | sed -e 's|version=||g' -e 's|[\x22, \t]||g'", returnStdout: true)
                    // update version number depending if the release_type is
                    // "BUGFIX OR MINOR IMPROVEMENT" (increase MINOR) or "BIG REVISION" (inc. MAJOR)
                    if( params.release_type == 'BUGFIX OR MINOR IMPROVEMENT'){
                        VERSION_NUMBER = sh(script: "echo ${VERSION_NUMBER} | awk -F'.' '{printf \"%d.%d\",$1,$2+1}'", returnStdout: true)
                    } else {
                        VERSION_NUMBER = sh(script: "echo ${VERSION_NUMBER} | awk -F'.' '{printf \"%d.%d\",$1+1,$2}'", returnStdout: true)
                    }
                }
            }
        }
        stage('Merging to master & Tagging') {
            when {
                branch 'develop'
            }
            steps {
                // sshagent(credentials: ['bitbucket_jenkins_1704']) {
                //     git branch: 'master', url: 'git@bitbucket.org:wiris/plugins.git';
                //     sh(script: 'git fetch --all');
                //     sh(script: 'git checkout master');
                //     sh(script: 'git merge origin/develop --ff-only');
                //     sh(script: 'git push origin master');
                //     sh(script: "git tag ${VERSION_NUMBER}")
                // }
                sh(script: "echo git tag ${VERSION_NUMBER}")
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
                WHEEL_NAME = sh(script: "dist/Santoku-*.whl", returnStdout: true)
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
                env.AWS_ACCESS_KEY_ID = AWS_ACCESS_CREDENTIALS_USR
                env.AWS_SECRET_ACCESS_KEY = AWS_ACCESS_CREDENTIALS_PSW
                env.AWS_DEFAULT_REGION = 'eu-west-1'
                sh(script: "echo aws s3 cp ${WHEEL_NAME} ${BUCKET_URL}")
            }
        }
    }
}
