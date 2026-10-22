# Deployment views: the same containers in four environments.

deployment seatlock "Development" "deploy-dev" "Docker Compose on a developer machine." {
    include *
    autolayout lr
}

deployment seatlock "AWS Demo" "deploy-aws-demo" "The demo on AWS. One availability zone, no NAT gateway, tasks in public subnets. Secrets, logs and alarms are on the demo ops view." {
    include *
    exclude demoSecrets demoLogs demoTopic demoEcr
    autolayout lr
}

deployment seatlock "AWS Demo" "deploy-aws-demo-ops" "The supporting services around the tasks in the demo: image registry, secrets, logs and alarms." {
    include demoApi demoWorker demoEcr demoSecrets demoLogs demoTopic
    autolayout lr
}

deployment seatlock "AWS Production" "deploy-aws-prod" "Production-like on AWS. Multi-AZ database, replica, NAT gateway, tasks in private subnets." {
    include *
    exclude prodSecrets prodLogs prodTopic prodEcr
    autolayout lr
}

deployment seatlock "AWS Production" "deploy-aws-ops" "The supporting services around the tasks in production: image registry, secrets, logs and alarms." {
    include prodApi prodWorker prodEcr prodSecrets prodLogs prodTopic
    autolayout lr
}

deployment seatlock "CI" "deploy-ci" "The backend job and the load test job in GitHub Actions." {
    include *
    autolayout lr
}
