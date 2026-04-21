"""
Static curated map of SaaS domain categories to real vendor recommendations.
Each vendor has a name, URL, and a one-line pitch tailored to the domain signal.
"""

VENDOR_MAP: dict[str, list[dict]] = {
    "observability_monitoring": [
        {"name": "Datadog", "url": "https://datadoghq.com", "pitch": "Full-stack observability with APM, logs, metrics, and distributed tracing in one platform"},
        {"name": "Honeycomb", "url": "https://honeycomb.io", "pitch": "Observability for complex distributed systems with high-cardinality event-driven debugging"},
        {"name": "Grafana Cloud", "url": "https://grafana.com/products/cloud", "pitch": "Open-source-native metrics, logs, and traces with Prometheus and Loki at scale"},
        {"name": "New Relic", "url": "https://newrelic.com", "pitch": "Unified observability platform with AI-assisted anomaly detection and full-stack visibility"},
        {"name": "Elastic Observability", "url": "https://elastic.co/observability", "pitch": "Unified logs, metrics, and APM built on the Elastic Stack"},
    ],
    "auth_identity_sso": [
        {"name": "Auth0", "url": "https://auth0.com", "pitch": "Drop-in authentication and authorization with enterprise SSO, MFA, and social login"},
        {"name": "Okta", "url": "https://okta.com", "pitch": "Enterprise identity platform with workforce and customer identity solutions"},
        {"name": "Clerk", "url": "https://clerk.com", "pitch": "Developer-first auth with pre-built UI components, sessions, and user management"},
        {"name": "WorkOS", "url": "https://workos.com", "pitch": "Enterprise-ready SSO, directory sync, and audit logs in a single API"},
        {"name": "Stytch", "url": "https://stytch.com", "pitch": "Passwordless auth and fraud detection with B2B and B2C identity primitives"},
    ],
    "messaging_event_streaming": [
        {"name": "Confluent", "url": "https://confluent.io", "pitch": "Fully managed Kafka with stream processing, connectors, and governance at enterprise scale"},
        {"name": "Redpanda", "url": "https://redpanda.com", "pitch": "Kafka-compatible streaming platform with 10x lower latency and no JVM overhead"},
        {"name": "Upstash", "url": "https://upstash.com", "pitch": "Serverless Kafka and Redis with per-request pricing, ideal for event-driven architectures"},
        {"name": "Pusher", "url": "https://pusher.com", "pitch": "Hosted WebSocket infrastructure for real-time messaging and pub/sub at scale"},
        {"name": "Ably", "url": "https://ably.com", "pitch": "Reliable realtime messaging platform with guaranteed delivery and global edge network"},
    ],
    "data_pipeline_etl": [
        {"name": "Fivetran", "url": "https://fivetran.com", "pitch": "Automated data movement with 500+ pre-built connectors and zero-maintenance pipelines"},
        {"name": "dbt Labs", "url": "https://getdbt.com", "pitch": "Transform data in your warehouse with SQL-first, version-controlled data models"},
        {"name": "Airbyte", "url": "https://airbyte.com", "pitch": "Open-source data integration with 350+ connectors and a self-hosted or cloud option"},
        {"name": "Estuary Flow", "url": "https://estuary.dev", "pitch": "Real-time CDC and streaming ETL with millisecond latency from source to destination"},
        {"name": "Meltano", "url": "https://meltano.com", "pitch": "Open-source ELT framework built on Singer taps with GitOps-friendly pipeline management"},
    ],
    "cicd_devops": [
        {"name": "CircleCI", "url": "https://circleci.com", "pitch": "Fast CI/CD with Docker-native builds, test splitting, and enterprise-grade security"},
        {"name": "BuildKite", "url": "https://buildkite.com", "pitch": "Hybrid CI with your own infrastructure, unlimited parallelism, and plugin ecosystem"},
        {"name": "Depot", "url": "https://depot.dev", "pitch": "Remote Docker build acceleration — drop-in replacement that makes builds 20x faster"},
        {"name": "Nx Cloud", "url": "https://nx.app", "pitch": "Distributed task execution and remote caching for monorepo CI pipelines"},
        {"name": "Trunk", "url": "https://trunk.io", "pitch": "Merge queue, flaky test detection, and code quality checks in a single DevEx platform"},
    ],
    "database_data_storage": [
        {"name": "PlanetScale", "url": "https://planetscale.com", "pitch": "Serverless MySQL with non-blocking schema changes, branching, and horizontal sharding"},
        {"name": "Neon", "url": "https://neon.tech", "pitch": "Serverless Postgres with branching, autoscaling, and instant database provisioning"},
        {"name": "Turso", "url": "https://turso.tech", "pitch": "Edge-native SQLite with per-tenant databases, low latency, and multi-region replication"},
        {"name": "CockroachDB", "url": "https://cockroachlabs.com", "pitch": "Distributed SQL database with global geo-partitioning, strong consistency, and 99.99% uptime SLA"},
        {"name": "Tigris", "url": "https://tigrisdata.com", "pitch": "Globally distributed object storage with S3-compatible API and automatic data tiering"},
    ],
    "security_compliance": [
        {"name": "Snyk", "url": "https://snyk.io", "pitch": "Developer-first security scanning for code, containers, IaC, and open-source dependencies"},
        {"name": "Vanta", "url": "https://vanta.com", "pitch": "Automated SOC 2, ISO 27001, and HIPAA compliance with continuous control monitoring"},
        {"name": "Drata", "url": "https://drata.com", "pitch": "Compliance automation platform with 75+ integrations and evidence collection built in"},
        {"name": "Socket", "url": "https://socket.dev", "pitch": "Supply chain security for npm, PyPI, and Go modules with real-time threat detection"},
        {"name": "Semgrep", "url": "https://semgrep.dev", "pitch": "Static analysis and secrets detection with custom rule support for any language"},
    ],
    "search": [
        {"name": "Algolia", "url": "https://algolia.com", "pitch": "Hosted search and discovery API with sub-10ms response times and AI ranking"},
        {"name": "Typesense", "url": "https://typesense.org", "pitch": "Open-source typo-tolerant search engine with instant results and easy self-hosting"},
        {"name": "Elastic Search", "url": "https://elastic.co/elasticsearch", "pitch": "Battle-tested distributed search with full-text, vector, and hybrid search capabilities"},
        {"name": "Meilisearch", "url": "https://meilisearch.com", "pitch": "Lightning-fast open-source search with faceting, filtering, and semantic search support"},
        {"name": "Glean", "url": "https://glean.com", "pitch": "AI-powered enterprise search across all company apps with personalized results and chat"},
    ],
    "feature_flags": [
        {"name": "LaunchDarkly", "url": "https://launchdarkly.com", "pitch": "Enterprise feature management with targeting, experimentation, and release automation"},
        {"name": "Statsig", "url": "https://statsig.com", "pitch": "Feature flags, A/B testing, and product analytics unified in a single experimentation platform"},
        {"name": "Unleash", "url": "https://getunleash.io", "pitch": "Open-source feature flag service with enterprise SSO, audit logs, and self-hosting options"},
        {"name": "Flagsmith", "url": "https://flagsmith.com", "pitch": "Open-source feature flags and remote config with segment targeting and SDK for every platform"},
    ],
    "api_gateway_service_mesh": [
        {"name": "Kong", "url": "https://konghq.com", "pitch": "API gateway and service mesh with plugins for auth, rate limiting, and observability"},
        {"name": "Apigee", "url": "https://cloud.google.com/apigee", "pitch": "Enterprise API management with analytics, developer portal, and hybrid deployment"},
        {"name": "Tyk", "url": "https://tyk.io", "pitch": "Open-source API gateway with GraphQL support, analytics, and on-premise or cloud deployment"},
        {"name": "Traefik Labs", "url": "https://traefik.io", "pitch": "Cloud-native API gateway and ingress controller with automatic service discovery"},
    ],
    "testing_qa": [
        {"name": "Playwright", "url": "https://playwright.dev", "pitch": "Microsoft's end-to-end testing framework with cross-browser support and trace viewer"},
        {"name": "Sauce Labs", "url": "https://saucelabs.com", "pitch": "Cloud-based test execution across 800+ browser/OS combinations with AI failure analysis"},
        {"name": "Mabl", "url": "https://mabl.com", "pitch": "Low-code intelligent test automation with auto-healing, visual testing, and CI integration"},
        {"name": "Checkly", "url": "https://checklyhq.com", "pitch": "Monitoring-as-code for APIs and Playwright tests with alerting and Vercel/Netlify integration"},
        {"name": "Chromatic", "url": "https://chromatic.com", "pitch": "Visual regression testing for Storybook components with PR review workflows"},
    ],
    "infrastructure_iac": [
        {"name": "Pulumi", "url": "https://pulumi.com", "pitch": "Infrastructure as code using real programming languages with state management and policy-as-code"},
        {"name": "Terraform Cloud", "url": "https://terraform.io", "pitch": "Managed Terraform with remote state, team workflows, audit logs, and Sentinel policy"},
        {"name": "Env0", "url": "https://env0.com", "pitch": "Self-service infrastructure with cost management, drift detection, and GitOps workflows"},
        {"name": "Spacelift", "url": "https://spacelift.io", "pitch": "Flexible IaC management supporting Terraform, OpenTofu, Pulumi, and Ansible"},
        {"name": "Gruntwork", "url": "https://gruntwork.io", "pitch": "Production-grade Terraform modules and a DevOps platform for landing zone bootstrapping"},
    ],
    "cdn_edge_networking": [
        {"name": "Cloudflare", "url": "https://cloudflare.com", "pitch": "Global CDN, DDoS protection, edge compute, and Zero Trust networking in one platform"},
        {"name": "Fastly", "url": "https://fastly.com", "pitch": "Programmable CDN with real-time purging, edge compute, and 99.99% uptime SLA"},
        {"name": "Vercel Edge Network", "url": "https://vercel.com/docs/edge-network", "pitch": "Globally distributed edge runtime co-located with Vercel deployments for zero-latency rendering"},
        {"name": "Bunny.net", "url": "https://bunny.net", "pitch": "Cost-effective CDN and edge storage with 100+ PoPs and smart geographic routing"},
    ],
    "payments_billing": [
        {"name": "Stripe", "url": "https://stripe.com", "pitch": "Full-stack payments infrastructure with subscriptions, invoicing, tax, and fraud detection"},
        {"name": "Lago", "url": "https://getlago.com", "pitch": "Open-source metered billing engine for usage-based pricing with real-time aggregation"},
        {"name": "Paddle", "url": "https://paddle.com", "pitch": "Merchant of record payments for SaaS with global tax compliance and subscription management"},
        {"name": "Stigg", "url": "https://stigg.io", "pitch": "Pricing and packaging infrastructure with feature entitlements, paywalls, and billing integration"},
    ],
    "notifications_comms": [
        {"name": "Knock", "url": "https://knock.app", "pitch": "Notification infrastructure with multi-channel routing, preferences, and a visual workflow builder"},
        {"name": "Novu", "url": "https://novu.co", "pitch": "Open-source notification infrastructure with in-app, email, SMS, push, and Slack channels"},
        {"name": "Courier", "url": "https://courier.com", "pitch": "Unified notification API with a drag-and-drop template editor and per-user channel preferences"},
        {"name": "Resend", "url": "https://resend.com", "pitch": "Developer-first transactional email built on React Email with deliverability analytics"},
    ],
    "ml_ai_platform": [
        {"name": "Weights & Biases", "url": "https://wandb.ai", "pitch": "ML experiment tracking, model registry, and LLM monitoring in a unified developer platform"},
        {"name": "Modal", "url": "https://modal.com", "pitch": "Serverless GPU compute for ML inference and training with instant cold starts and Python-native SDK"},
        {"name": "Replicate", "url": "https://replicate.com", "pitch": "Run and fine-tune open-source models via API with per-second GPU billing"},
        {"name": "Baseten", "url": "https://baseten.co", "pitch": "ML model serving with custom inference pipelines, GPU autoscaling, and low-latency deployment"},
        {"name": "LangSmith", "url": "https://smith.langchain.com", "pitch": "LLM observability and evaluation platform for debugging, testing, and monitoring AI applications"},
    ],
    "analytics_bi": [
        {"name": "Mixpanel", "url": "https://mixpanel.com", "pitch": "Product analytics with funnel analysis, cohorts, and real-time event tracking for growth teams"},
        {"name": "PostHog", "url": "https://posthog.com", "pitch": "Open-source product analytics with feature flags, session recording, and A/B testing"},
        {"name": "Metabase", "url": "https://metabase.com", "pitch": "Self-service BI with a no-SQL query builder, dashboards, and embedded analytics"},
        {"name": "Amplitude", "url": "https://amplitude.com", "pitch": "Digital analytics platform with behavioral graphs, predictive cohorts, and experimentation"},
        {"name": "Segment", "url": "https://segment.com", "pitch": "Customer data platform that collects, cleans, and routes event data to 300+ destinations"},
    ],
    "support_ticketing": [
        {"name": "Plain", "url": "https://plain.com", "pitch": "Developer-first customer support with API-first design, triage workflows, and Slack integration"},
        {"name": "Intercom", "url": "https://intercom.com", "pitch": "AI-first customer service platform with inbox, chatbot, and product tours in one suite"},
        {"name": "Linear", "url": "https://linear.app", "pitch": "Issue tracking built for engineering teams with Git integration, cycles, and roadmaps"},
        {"name": "Zendesk", "url": "https://zendesk.com", "pitch": "Enterprise support platform with omnichannel ticketing, AI triage, and a self-service portal"},
    ],
    "ecommerce": [
        {"name": "Shopify Plus", "url": "https://shopify.com/plus", "pitch": "Enterprise ecommerce platform with headless APIs, automation, and global payment processing"},
        {"name": "Commerce Layer", "url": "https://commercelayer.io", "pitch": "Headless commerce API for multi-market, multi-currency storefronts with order management"},
        {"name": "Medusa", "url": "https://medusajs.com", "pitch": "Open-source composable commerce engine with a modular plugin architecture and REST + GraphQL APIs"},
        {"name": "Swell", "url": "https://swell.is", "pitch": "Headless ecommerce platform with subscriptions, B2B, and customizable checkout flows"},
        {"name": "Feedonomics", "url": "https://feedonomics.com", "pitch": "Full-service product feed management for marketplace and ad channel syndication at scale"},
    ],
    "marketing_communications": [
        {"name": "Customer.io", "url": "https://customer.io", "pitch": "Behavioral messaging platform for triggered email, push, and SMS based on real-time user data"},
        {"name": "Braze", "url": "https://braze.com", "pitch": "Enterprise customer engagement platform with cross-channel journeys and real-time personalization"},
        {"name": "Loops", "url": "https://loops.so", "pitch": "Email platform built for SaaS with transactional and marketing flows in a single tool"},
        {"name": "Iterable", "url": "https://iterable.com", "pitch": "Cross-channel growth marketing platform with drag-and-drop journey builder and AI send-time optimization"},
    ],
}


def get_vendors_for_domains(signals: list[dict]) -> list[dict]:
    """
    Look up vendors for a list of classified signals.
    Only returns results for high and medium confidence signals.

    Args:
        signals: List of {domain, confidence, reasoning} dicts from classify_signal

    Returns:
        List of {domain, confidence, reasoning, vendors} dicts
    """
    results = []
    for signal in signals:
        if signal.get("confidence") not in ("high", "medium"):
            continue
        domain = signal.get("domain", "")
        vendors = VENDOR_MAP.get(domain, [])
        if vendors:
            results.append({
                "domain": domain,
                "confidence": signal["confidence"],
                "reasoning": signal.get("reasoning", ""),
                "vendors": vendors,
            })
    return results
