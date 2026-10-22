# Level 3: components.

component spa "spa-components" "Level 3. The single-page app." {
    include *
    autolayout tb
}

component api "api-components" "Level 3. The API in four layers: interface, application, domain and infrastructure. Dependencies point inward. Which adapter implements which port, and the email system, are on the ports-and-adapters view." {
    include *
    exclude aws email
    exclude "relationship.tag==Runtime"
    exclude "relationship.tag==Wiring"
    exclude "relationship.tag==Implements"
    autolayout lr
}

component api "api-interface" "The interface layer: what the single-page app can call, and what each endpoint uses." {
    include spa workshopsApi organizerApi accountsApi healthApi rateLimits
    include queries listCache redis database
    exclude "relationship.tag==Runtime"
    autolayout lr
}

component api "api-core" "The core: use cases, the ports they depend on and the seat rules. No Django, no Celery." {
    include compositionRoot registerUseCase cancelUseCase promoteUseCase ports entities
    exclude "relationship.tag==Runtime"
    exclude "relationship.tag==Wiring"
    autolayout tb
}

component api "api-ports-adapters" "The ports and the adapters that implement them. The composition root picks the adapters. The use cases know the ports and never the adapters." {
    include compositionRoot ports unitOfWork repositories listCache queueAdapter notifier
    include database redis email
    exclude "relationship.tag==Runtime"
    autolayout tb
}

component worker "worker-components" "Level 3. The worker runs the same code as the API, started by a queue message." {
    include *
    autolayout lr
}
