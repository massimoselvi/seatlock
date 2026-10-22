styles {
    element "Person" {
        shape Person
        background #1e1b4b
        color #ffffff
    }
    element "Software System" {
        background #4f46e5
        color #ffffff
    }
    element "External" {
        background #64748b
        color #ffffff
    }
    element "Container" {
        background #6366f1
        color #ffffff
    }
    element "Browser App" {
        shape WebBrowser
        background #0284c7
    }
    element "Backend" {
        background #4338ca
    }
    element "Database" {
        shape Cylinder
        background #0f766e
    }
    element "Cache" {
        background #b45309
    }
    element "Tooling" {
        background #475569
    }
    element "Async" {
        border dashed
    }

    # Components are colored by layer, so the dependency rule can be read from the colors.
    element "Component" {
        background #c7d2fe
        color #1e1b4b
    }
    element "Frontend" {
        background #bae6fd
        color #0c4a6e
    }
    element "Interface" {
        background #e9d5ff
        color #3b0764
    }
    element "Application" {
        background #a5b4fc
        color #1e1b4b
    }
    element "Domain" {
        background #6ee7b7
        color #022c22
    }
    element "Infrastructure" {
        background #fde68a
        color #451a03
    }
    element "Bypass" {
        border dashed
        stroke #dc2626
        strokeWidth 4
    }

    element "Deployment Node" {
        background #ffffff
        color #0f172a
        stroke #94a3b8
    }
    element "AWS" {
        stroke #ea580c
    }
    element "Infrastructure Node" {
        shape RoundedBox
        background #fff7ed
        color #7c2d12
        stroke #ea580c
    }

    # Solid by default, so the dashed purple lines stand out as the work done through the queue.
    relationship "Relationship" {
        dashed false
        color #475569
        thickness 2
    }
    relationship "Async" {
        dashed true
        color #7c3aed
    }
    relationship "Implements" {
        dashed true
        color #94a3b8
    }
    relationship "Bypass" {
        dashed true
        color #dc2626
    }
}
