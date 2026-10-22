# Where the containers run. Sources: compose.yaml, infra/ (CDK stacks and config.py), .github/workflows/.

deploymentEnvironment "Development" {
    deploymentNode "Developer machine" "macOS or Linux with Docker" "Docker" {
        devBrowserNode = deploymentNode "Web browser" "Runs the single-page app." "Chrome, Firefox or Safari" {
            devSpa = containerInstance spa
        }
        deploymentNode "Docker Compose" "docker compose up --build" "Docker Compose" {
            devVite = infrastructureNode "frontend" "Vite dev server on port 5173. Proxies /api to web." "node:22-alpine, pnpm dev"
            deploymentNode "web" "Applies migrations, then runs the Django dev server on port 8000. The load test runs inside it." "python:3.13, runserver" {
                devApi = containerInstance api
                devLoadTest = containerInstance loadTest
            }
            deploymentNode "worker" "Takes tasks from Redis database 0." "python:3.13, celery worker" {
                devWorker = containerInstance worker
            }
            deploymentNode "db" "Volume pgdata. Port 5432." "postgres:17-alpine" {
                devDb = containerInstance database
            }
            deploymentNode "redis" "Broker is database 0. Cache is database 1." "redis:7-alpine" {
                devRedis = containerInstance redis
            }
            devMail = infrastructureNode "Console email backend" "Prints the promotion email to the web and worker logs." "Django EMAIL_BACKEND"
        }
    }
    devSpa -> devVite "Loads the app" "HTTP"
    devVite -> devApi "Proxies /api/*" "HTTP"
    devWorker -> devMail "Prints the email" "Django email backend"
}

deploymentEnvironment "AWS Demo" {
    deploymentNode "User's device" "The attendee or the organizer." "Laptop or phone" {
        demoBrowser = deploymentNode "Web browser" "Runs the single-page app." "Chrome, Firefox or Safari" {
            demoSpa = containerInstance spa
        }
    }
    deploymentNode "Amazon Web Services" "One account. Region eu-west-1. Four CDK stacks: Network, Data, App, Frontend. Cost about 0.12 to 0.16 an hour." "AWS" "AWS" {
        demoCdn = infrastructureNode "CloudFront" "One domain with TLS. Site files from S3. /api/* goes to the load balancer over HTTP." "Amazon CloudFront" "${AWS_CLOUDFRONT}"
        demoBucket = infrastructureNode "S3 bucket" "Holds the Vue build. Private, reached through origin access control." "Amazon S3" "${AWS_S3}"
        demoEcr = infrastructureNode "ECR repository" "seatlock-backend. Scans on push. Keeps the last 20 images." "Amazon ECR" "${AWS_ECR}"
        demoSecrets = infrastructureNode "Secrets Manager" "Django secret key and the database password. Injected into tasks as secrets." "AWS Secrets Manager" "${AWS_SECRETS}"
        demoLogs = infrastructureNode "CloudWatch" "Logs kept for one month. Four alarms from the SLO document." "Amazon CloudWatch" "${AWS_CLOUDWATCH}"
        demoTopic = infrastructureNode "SNS topic" "Sends the alarm email." "Amazon SNS" "${AWS_SNS}"
        deploymentNode "VPC" "Two availability zones. No NAT gateway." "Amazon VPC" "${AWS_VPC}" {
            demoAlb = infrastructureNode "Application Load Balancer" "Accepts traffic only from CloudFront. Health check on /api/health/. Blocks /admin." "Elastic Load Balancing" "${AWS_ALB}"
            deploymentNode "Public subnets" "Tasks get public IP addresses, because there is no NAT gateway." "Amazon VPC subnets" {
                deploymentNode "ECS cluster" "Runs the web and the worker service." "Amazon ECS on Fargate" "${AWS_ECS}" {
                    deploymentNode "Web service" "0.5 vCPU, 1 GB. Rolling deploy with a circuit breaker." "ECS service" "${AWS_FARGATE}" 2 {
                        demoApi = containerInstance api
                    }
                    deploymentNode "Worker service" "0.25 vCPU, 0.5 GB." "ECS service" "${AWS_FARGATE}" 1 {
                        demoWorker = containerInstance worker
                    }
                }
            }
            deploymentNode "Isolated data subnets" "No route to the internet." "Amazon VPC subnets" {
                deploymentNode "RDS" "db.t4g.micro, 20 GB gp3, encrypted, one availability zone, 1 day of backups." "Amazon RDS for PostgreSQL 17" "${AWS_RDS}" {
                    demoDb = containerInstance database
                }
                deploymentNode "ElastiCache" "cache.t4g.micro, one node, TLS and encryption at rest." "Amazon ElastiCache for Redis" "${AWS_ELASTICACHE}" {
                    demoRedis = containerInstance redis
                }
            }
        }
    }
    demoSpa -> demoCdn "Loads the site and calls /api/*" "HTTPS"
    demoCdn -> demoBucket "Gets the site files" "HTTPS"
    demoCdn -> demoAlb "Forwards /api/*" "HTTP"
    demoAlb -> demoApi "Forwards requests" "HTTP, port 8000"
    demoApi -> demoSecrets "Gets secrets at start" "HTTPS"
    demoApi -> demoEcr "Image is pulled from it at start" "HTTPS"
    demoWorker -> demoEcr "Image is pulled from it at start" "HTTPS"
    demoApi -> demoLogs "Writes logs" "HTTPS"
    demoWorker -> demoLogs "Writes logs" "HTTPS"
    demoLogs -> demoTopic "Alarms publish to" "SNS"
}

deploymentEnvironment "AWS Production" {
    deploymentNode "User's device" "The attendee or the organizer." "Laptop or phone" {
        prodBrowser = deploymentNode "Web browser" "Runs the single-page app." "Chrome, Firefox or Safari" {
            prodSpa = containerInstance spa
        }
    }
    deploymentNode "Amazon Web Services" "Same four stacks as the demo. Only the values in config.py differ. Cost about 0.23 an hour." "AWS" "AWS" {
        prodCdn = infrastructureNode "CloudFront" "One domain with TLS. Site files from S3. /api/* goes to the load balancer over HTTP." "Amazon CloudFront" "${AWS_CLOUDFRONT}"
        prodBucket = infrastructureNode "S3 bucket" "Holds the Vue build. Private. Kept when the stack is deleted." "Amazon S3" "${AWS_S3}"
        prodEcr = infrastructureNode "ECR repository" "seatlock-backend. Scans on push. Kept when the stack is deleted." "Amazon ECR" "${AWS_ECR}"
        prodSecrets = infrastructureNode "Secrets Manager" "Django secret key and the database password." "AWS Secrets Manager" "${AWS_SECRETS}"
        prodLogs = infrastructureNode "CloudWatch" "Logs kept for one month. Four alarms from the SLO document." "Amazon CloudWatch" "${AWS_CLOUDWATCH}"
        prodTopic = infrastructureNode "SNS topic" "Sends the alarm email." "Amazon SNS" "${AWS_SNS}"
        deploymentNode "VPC" "Two availability zones." "Amazon VPC" "${AWS_VPC}" {
            prodAlb = infrastructureNode "Application Load Balancer" "Accepts traffic only from CloudFront. Health check on /api/health/. Blocks /admin." "Elastic Load Balancing" "${AWS_ALB}"
            prodNat = infrastructureNode "NAT gateway" "Lets the private tasks reach ECR, Secrets Manager and the internet." "Amazon VPC" "${AWS_NAT}"
            deploymentNode "Private subnets" "Tasks have no public IP addresses." "Amazon VPC subnets" {
                deploymentNode "ECS cluster" "Runs the web and the worker service." "Amazon ECS on Fargate" "${AWS_ECS}" {
                    deploymentNode "Web service" "0.5 vCPU, 1 GB. Rolling deploy with a circuit breaker." "ECS service" "${AWS_FARGATE}" 2 {
                        prodApi = containerInstance api
                    }
                    deploymentNode "Worker service" "0.25 vCPU, 0.5 GB." "ECS service" "${AWS_FARGATE}" 1 {
                        prodWorker = containerInstance worker
                    }
                }
            }
            deploymentNode "Isolated data subnets" "No route to the internet." "Amazon VPC subnets" {
                deploymentNode "RDS primary" "db.t4g.micro, 20 GB gp3, encrypted, 7 days of backups, deletion protection." "Amazon RDS for PostgreSQL 17, Multi-AZ" "${AWS_RDS}" {
                    prodDb = containerInstance database
                }
                deploymentNode "RDS standby" "Second availability zone. Takes over in about one to two minutes." "Amazon RDS for PostgreSQL 17, Multi-AZ" "${AWS_RDS}" {
                    prodDbStandby = infrastructureNode "Standby instance" "Receives every change from the primary. Not used for reads." "Amazon RDS" "${AWS_RDS}"
                }
                deploymentNode "ElastiCache primary" "cache.t4g.micro, TLS and encryption at rest." "Amazon ElastiCache for Redis" "${AWS_ELASTICACHE}" {
                    prodRedis = containerInstance redis
                }
                deploymentNode "ElastiCache replica" "Second availability zone." "Amazon ElastiCache for Redis" "${AWS_ELASTICACHE}" {
                    prodRedisReplica = infrastructureNode "Replica" "A copy of the primary. Takes over when the primary fails." "Amazon ElastiCache" "${AWS_ELASTICACHE}"
                }
            }
        }
    }
    prodDb -> prodDbStandby "Replicates synchronously" "RDS Multi-AZ"
    prodRedis -> prodRedisReplica "Replicates" "ElastiCache"
    prodSpa -> prodCdn "Loads the site and calls /api/*" "HTTPS"
    prodCdn -> prodBucket "Gets the site files" "HTTPS"
    prodCdn -> prodAlb "Forwards /api/*" "HTTP"
    prodAlb -> prodApi "Forwards requests" "HTTP, port 8000"
    prodApi -> prodNat "Reaches AWS APIs through" "HTTPS"
    prodApi -> prodSecrets "Gets secrets at start" "HTTPS"
    prodApi -> prodEcr "Image is pulled from it at start" "HTTPS"
    prodWorker -> prodEcr "Image is pulled from it at start" "HTTPS"
    prodApi -> prodLogs "Writes logs" "HTTPS"
    prodWorker -> prodLogs "Writes logs" "HTTPS"
    prodLogs -> prodTopic "Alarms publish to" "SNS"
}

deploymentEnvironment "CI" {
    deploymentNode "GitHub" "Runs the workflows on every pull request." "github.com" {
        deploymentNode "Backend job" "ci.yml. ruff, migrations check, deploy check, pytest with coverage. The frontend job runs pnpm run ci. The infra job runs ruff, pytest and cdk synth." "GitHub-hosted runner, ubuntu-latest" {
            deploymentNode "PostgreSQL service (backend job)" "postgres:17-alpine" "Service container" {
                ciBackendDb = containerInstance database
            }
        }
        deploymentNode "Load test job" "load-test.yml. Runs on pull requests that touch seat code and by hand. Two jobs: 4 workers x 1 thread and 4 workers x 8 threads." "GitHub-hosted runner, ubuntu-latest" {
            deploymentNode "gunicorn" "Started by the script on a free port." "gunicorn" {
                ciApi = containerInstance api
            }
            deploymentNode "celery worker" "Started in the background. Scenario C needs it." "Celery" {
                ciWorker = containerInstance worker
            }
            deploymentNode "PostgreSQL service" "postgres:17-alpine" "Service container" {
                ciDb = containerInstance database
            }
            deploymentNode "Redis service" "redis:7-alpine" "Service container" {
                ciRedis = containerInstance redis
            }
            deploymentNode "load_test.py" "Fires the requests, checks the database, writes a summary and an artifact." "Python" {
                ciLoadTest = containerInstance loadTest
            }
        }
    }
}
