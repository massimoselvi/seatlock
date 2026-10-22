workspace "Seatlock" "Workshops with limited seats, built so a seat can never be sold twice." {

    # Flat identifiers: every element name is unique across the whole model.
    !identifiers flat

    # Every relationship is written out. The API image also holds the code that runs in the worker,
    # so a derived relationship would draw the API sending email.
    !impliedRelationships false

    # Tag names from the AWS theme, used for the icons in the deployment views.
    !include aws-tags.dsl

    model {
        !include model/context.dsl
        !include model/seatlock.dsl
        !include model/relationships.dsl
        !include model/deployment.dsl
    }

    configuration {
        scope softwaresystem
    }

    views {
        !include views/context.dsl
        !include views/containers.dsl
        !include views/components.dsl
        !include views/dynamic.dsl
        !include views/deployment.dsl
        !include styles.dsl
    }
}
