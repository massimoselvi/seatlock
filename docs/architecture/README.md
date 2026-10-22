# Architecture diagrams (C4)

The architecture of Seatlock as a [C4 model](https://c4model.com/), written in the [Structurizr DSL](https://docs.structurizr.com/dsl).

- **The source** is `workspace.dsl` and the files it includes. This is the one place to edit.
- **The images** in `diagrams/` are generated from the source. Do not edit them.
- **Written explanation** is in [../architecture.md](../architecture.md), with sequence diagrams in Mermaid. Read that for the reasoning and this folder for the structure. They describe the same system. When the structure changes, update both.

## View the diagrams

On GitHub, the images below render in this page. Click one to open it full size and zoom.

For the interactive version, with pan, zoom, the documentation pages and a link on each component to its code:

```bash
docker run --rm -p 8080:8080 -v "$PWD/docs/architecture":/usr/local/structurizr \
  structurizr/structurizr:2026.09.19 local
```

Open <http://localhost:8080>. The first start writes `workspace.json` and `.structurizr/` in this folder. Git ignores both. It needs internet access: it downloads the AWS icon theme from GitHub when it reads the workspace.

> **About Structurizr Lite.** The `structurizr/lite` image is the tool this workspace was planned for. Its latest tag is now a stub: it prints a deprecation notice and exits. The maintained replacement is the `local` command of `structurizr/structurizr`, used above. It takes the same folder, the same port and the same DSL. If you need the old tool, `structurizr/lite:2025.11.08` was the last working tag. It gets no updates.

## The views

### Level 1: system context

Who uses Seatlock, and which systems it talks to.

| View | Shows |
|------|-------|
| `landscape` | Everything: people, Seatlock, and every system around it. |
| `context` | Seatlock, its users and the email service, while it runs. |
| `delivery` | How code gets built, tested and onto AWS. |

![landscape](diagrams/landscape.svg)
![context](diagrams/context.svg)
![delivery](diagrams/delivery.svg)

### Level 2: containers

What runs, and how the parts talk.

| View | Shows |
|------|-------|
| `containers` | The five containers, the people and the email service. |
| `containers-async` | Only the work done through the queue (dashed purple lines). |
| `containers-all` | Everything, with the load test tool and the people who run it. |

![containers](diagrams/containers.svg)
![containers-async](diagrams/containers-async.svg)
![containers-all](diagrams/containers-all.svg)

### Level 3: components

What is inside the three containers that hold code. Components are colored by layer, so the dependency rule can be read from the colors.

| View | Shows |
|------|-------|
| `spa-components` | The single-page app: shell, auth, list, dashboard, theme, session, API client. |
| `api-components` | The API in four layers. The overview. |
| `api-interface` | The interface layer and what each endpoint uses. |
| `api-core` | The core: use cases, ports, seat rules. No framework. |
| `api-ports-adapters` | Which adapter implements which port, and what the composition root picks. |
| `worker-components` | The worker, which runs the same code as the API. |

![spa-components](diagrams/spa-components.svg)
![api-components](diagrams/api-components.svg)
![api-interface](diagrams/api-interface.svg)
![api-core](diagrams/api-core.svg)
![api-ports-adapters](diagrams/api-ports-adapters.svg)
![worker-components](diagrams/worker-components.svg)

### Dynamic views

One request, step by step. The numbers give the order.

| View | Shows |
|------|-------|
| `flow-register` | Register for a workshop. The lock comes before any seat count is read. |
| `flow-list` | Read the public list through the versioned cache. |
| `flow-signup` | Sign up, with the rate limit. |
| `flow-cancel-promote` | Cancel a seat. After the commit the queue promotes the oldest waitlisted user. |
| `flow-load-test` | The load test: 200 requests for 10 seats, then a check of the database. |

![flow-register](diagrams/flow-register.svg)
![flow-list](diagrams/flow-list.svg)
![flow-signup](diagrams/flow-signup.svg)
![flow-cancel-promote](diagrams/flow-cancel-promote.svg)
![flow-load-test](diagrams/flow-load-test.svg)

### Deployment views

The same containers in four environments.

| View | Shows |
|------|-------|
| `deploy-dev` | Docker Compose on a developer machine. |
| `deploy-aws-demo` | The AWS demo: one availability zone, no NAT gateway, tasks in public subnets. |
| `deploy-aws-demo-ops` | The demo's image registry, secrets, logs and alarms. |
| `deploy-aws-prod` | Production-like: Multi-AZ database, replica, NAT gateway, tasks in private subnets. |
| `deploy-aws-ops` | Production's image registry, secrets, logs and alarms. |
| `deploy-ci` | The backend job and the load test job in GitHub Actions. |

![deploy-dev](diagrams/deploy-dev.svg)
![deploy-aws-demo](diagrams/deploy-aws-demo.svg)
![deploy-aws-demo-ops](diagrams/deploy-aws-demo-ops.svg)
![deploy-aws-prod](diagrams/deploy-aws-prod.svg)
![deploy-aws-ops](diagrams/deploy-aws-ops.svg)
![deploy-ci](diagrams/deploy-ci.svg)

## How to read them

| Color | Layer or kind |
|-------|---------------|
| Light purple | interface: HTTP views, serializers, rate limits |
| Amber | infrastructure: Django, Celery, Redis, email |
| Blue | application: use cases and ports |
| Green | domain: the seat rules |
| Light blue | single-page app components |
| Teal cylinder | database |
| Orange cylinder | cache and broker |
| Gray box | external system |
| Red dashed border | bypasses the use cases and the lock (the Django admin) |

| Line | Meaning |
|------|---------|
| Solid | A call or a dependency. |
| Dashed purple | Work done through the queue, after the commit. |
| Dashed gray | An adapter implements a port. |

Dependencies point inward: interface, then infrastructure, then application, then domain. A test enforces it (`backend/tests/test_architecture.py`).

## How the model is built

| File | Holds |
|------|-------|
| `workspace.dsl` | The entry point. Includes the files below. |
| `model/context.dsl` | People and the external systems. |
| `model/seatlock.dsl` | The system, its containers and their components. Each component links to its code. |
| `model/relationships.dsl` | Every relationship, by level. |
| `model/deployment.dsl` | The four deployment environments. |
| `views/*.dsl` | The views. |
| `styles.dsl` | Colors, shapes and line styles. Loads the AWS icon theme. |
| `aws-tags.dsl` | The theme's tag names for the AWS services we use, as constants. |
| `documentation/*.md` | The pages shown next to the diagrams in the viewer. |
| `tools/` | The export tool and the checker. |

Conventions:

- **Flat identifiers.** Every name is unique across the model, for example `registerUseCase`.
- **No implied relationships** (`!impliedRelationships false`). Every relationship is written out. The API image also holds the code that runs in the worker, and a derived relationship would draw the API sending email.
- **Relationship tags.** `Runtime` marks a call that exists only while a request runs. It is used by the dynamic views and hidden in the static ones. `Async` marks work done through the queue. `Implements` marks an adapter that implements a port. `Wiring` marks what the composition root picks. `Bypass` marks the Django admin.
- **AWS icons.** The deployment views use the icons of the [Structurizr AWS theme](https://github.com/structurizr/themes/tree/master/amazon-web-services-2023.01.31). A node gets its icon from a tag, for example `"${AWS_CLOUDFRONT}"`. The tags are constants in `aws-tags.dsl`. To add an icon for another service, find its tag name in the theme's `theme.json`, add a `!const` line, and use it as the node's tag. The theme is read from GitHub, pinned to one commit, so the icons cannot change under the diagrams. The exported SVGs embed the icons, so they show on GitHub without loading anything. The icons belong to AWS and are used here only to draw the architecture.
- **One level of detail per view.** A view with more than about 12 elements stops being readable, so the API components are split into an overview and three focused views.

## Change the diagrams

1. Edit the DSL.
2. Check it. This must print nothing:

   ```bash
   docker run --rm -v "$PWD/docs/architecture":/usr/local/structurizr \
     structurizr/structurizr:2026.09.19 validate -workspace /usr/local/structurizr/workspace.dsl
   ```

3. Look at the result in the viewer (see above).
4. Regenerate the images. This needs Docker, Node 22 and pnpm, and a Chrome or Chromium:

   ```bash
   CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" docs/architecture/export.sh
   ```

   Without `CHROME_PATH`, install Playwright's browser once with `cd docs/architecture/tools && pnpm exec playwright-core install chromium`.
5. Commit the DSL and the images together.

A new view needs an entry in this README: the checker fails otherwise.

The inspector (`inspect` instead of `validate`) reports one finding on purpose: the system has no decisions. The importer reads the `Status:` line of our ADRs as "Proposed" and dates every ADR as today, so the decisions are listed by hand in `documentation/04-decisions.md`.

## Other formats

A static copy of the viewer, for hosting or for a machine without Docker:

```bash
docker run --rm -v "$PWD/docs/architecture":/usr/local/structurizr -v "$PWD/site":/out \
  structurizr/structurizr:2026.09.19 export -w /usr/local/structurizr/workspace.dsl -f static -o /out
```

The same command with `-f mermaid`, `-f plantuml` or `-f json` gives those formats. PNG and SVG come from `export.sh`, because this build of the exporter does not render images itself.

## Checks in CI

`.github/workflows/architecture.yml` runs on pull requests that touch this folder. It validates the workspace (the runner downloads the icon theme, like any other start) and runs `tools/check-diagrams.py`, which fails when a view has no image, an image has no view, or this page does not show a view. It does not redraw the images: the output changes a little on each run, so a diff would never be clean.
