pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    jenkins: agent
spec:
  containers:
  - name: docker
    image: docker:20.10
    command:
    - cat
    tty: true
    volumeMounts:
    - name: docker-sock
      mountPath: /var/run/docker.sock
  - name: kubectl
    image: bitnami/kubectl:latest
    command:
    - cat
    tty: true
  - name: python
    image: python:3.11
    command:
    - cat
    tty: true
  volumes:
  - name: docker-sock
    hostPath:
      path: /var/run/docker.sock
"""
        }
    }

    environment {
        DOCKER_REGISTRY = credentials('docker-registry')
        DOCKER_IMAGE = 'ai-orchestrator'
        KUBE_CONFIG = credentials('kubernetes-config')
        DEPLOYMENT_ENV = "${env.BRANCH_NAME == 'main' ? 'production' : 'staging'}"
        VERSION = "${env.GIT_COMMIT.take(8)}"
        DOCKER_TAG = "${DEPLOYMENT_ENV}-${VERSION}"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
        timeout(time: 1, unit: 'HOURS')
        timestamps()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_MSG = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
                    env.GIT_AUTHOR = sh(script: 'git log -1 --pretty=%an', returnStdout: true).trim()
                }
            }
        }

        stage('Setup') {
            steps {
                container('python') {
                    sh '''
                        pip install --upgrade pip
                        pip install -r requirements.txt
                        pip install pytest pytest-cov black flake8 mypy bandit
                    '''
                }
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Linting') {
                    steps {
                        container('python') {
                            sh '''
                                echo "Running Black..."
                                black --check orchestrator adapters tests || true

                                echo "Running Flake8..."
                                flake8 orchestrator adapters tests || true
                            '''
                        }
                    }
                }

                stage('Type Checking') {
                    steps {
                        container('python') {
                            sh 'mypy orchestrator adapters || true'
                        }
                    }
                }

                stage('Security Scan') {
                    steps {
                        container('python') {
                            sh 'bandit -r orchestrator adapters -f json -o bandit-report.json || true'
                        }
                    }
                }
            }
        }

        stage('Unit Tests') {
            steps {
                container('python') {
                    sh '''
                        pytest tests/ \
                            --cov=orchestrator \
                            --cov=adapters \
                            --cov-report=xml \
                            --cov-report=html \
                            --junitxml=pytest-report.xml \
                            -v
                    '''
                }
            }
            post {
                always {
                    junit 'pytest-report.xml'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                container('docker') {
                    sh """
                        docker build \
                            --build-arg VERSION=${VERSION} \
                            --build-arg BUILD_DATE=\$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
                            --build-arg VCS_REF=${GIT_COMMIT} \
                            -t ${DOCKER_IMAGE}:${DOCKER_TAG} \
                            -t ${DOCKER_IMAGE}:latest \
                            .
                    """
                }
            }
        }

        stage('Security Scan - Docker') {
            steps {
                container('docker') {
                    sh """
                        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
                            aquasec/trivy:latest image \
                            --severity HIGH,CRITICAL \
                            --exit-code 0 \
                            ${DOCKER_IMAGE}:${DOCKER_TAG}
                    """
                }
            }
        }

        stage('Push to Registry') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    branch 'staging'
                }
            }
            steps {
                container('docker') {
                    sh """
                        echo ${DOCKER_REGISTRY_PSW} | docker login -u ${DOCKER_REGISTRY_USR} --password-stdin
                        docker push ${DOCKER_IMAGE}:${DOCKER_TAG}
                        docker push ${DOCKER_IMAGE}:latest
                    """
                }
            }
        }

        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                container('kubectl') {
                    sh '''
                        kubectl config use-context staging
                        kubectl set image deployment/ai-orchestrator-blue \
                            ai-orchestrator=${DOCKER_IMAGE}:${DOCKER_TAG} \
                            -n ai-orchestrator
                        kubectl rollout status deployment/ai-orchestrator-blue -n ai-orchestrator
                    '''
                }
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            stages {
                stage('Blue/Green - Deploy Green') {
                    steps {
                        container('kubectl') {
                            sh '''
                                kubectl config use-context production

                                # Deploy to green environment
                                kubectl set image deployment/ai-orchestrator-green \
                                    ai-orchestrator=${DOCKER_IMAGE}:${DOCKER_TAG} \
                                    -n ai-orchestrator

                                # Scale up green deployment
                                kubectl scale deployment/ai-orchestrator-green --replicas=3 -n ai-orchestrator

                                # Wait for green to be ready
                                kubectl rollout status deployment/ai-orchestrator-green -n ai-orchestrator
                            '''
                        }
                    }
                }

                stage('Smoke Tests') {
                    steps {
                        script {
                            container('python') {
                                sh '''
                                    # Run smoke tests against green environment
                                    python scripts/smoke_tests.py --environment green
                                '''
                            }
                        }
                    }
                }

                stage('Switch Traffic') {
                    input {
                        message "Switch traffic to green environment?"
                        ok "Deploy"
                    }
                    steps {
                        container('kubectl') {
                            sh '''
                                # Switch service to point to green
                                kubectl patch service ai-orchestrator-service \
                                    -n ai-orchestrator \
                                    -p '{"spec":{"selector":{"version":"green"}}}'

                                echo "Traffic switched to green environment"
                                sleep 30
                            '''
                        }
                    }
                }

                stage('Verify Production') {
                    steps {
                        script {
                            container('python') {
                                sh '''
                                    # Run production verification tests
                                    python scripts/verify_deployment.py --environment production
                                '''
                            }
                        }
                    }
                }

                stage('Scale Down Blue') {
                    steps {
                        container('kubectl') {
                            sh '''
                                # Scale down blue environment
                                kubectl scale deployment/ai-orchestrator-blue --replicas=0 -n ai-orchestrator

                                # Swap labels: current green becomes new blue
                                echo "Blue/Green swap completed"
                            '''
                        }
                    }
                }
            }
        }

        stage('Rollback') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                container('kubectl') {
                    sh '''
                        echo "Rolling back deployment..."
                        kubectl rollout undo deployment/ai-orchestrator-blue -n ai-orchestrator
                    '''
                }
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        success {
            slackSend(
                color: 'good',
                message: """
                    ✅ Build Successful
                    Job: ${env.JOB_NAME}
                    Build: ${env.BUILD_NUMBER}
                    Environment: ${DEPLOYMENT_ENV}
                    Version: ${VERSION}
                    Author: ${env.GIT_AUTHOR}
                    Message: ${env.GIT_COMMIT_MSG}
                """
            )
        }
        failure {
            slackSend(
                color: 'danger',
                message: """
                    ❌ Build Failed
                    Job: ${env.JOB_NAME}
                    Build: ${env.BUILD_NUMBER}
                    Environment: ${DEPLOYMENT_ENV}
                    Version: ${VERSION}
                    Author: ${env.GIT_AUTHOR}
                    Check: ${env.BUILD_URL}
                """
            )
        }
    }
}
