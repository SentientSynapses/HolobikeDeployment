# Intelligence Integration

This integration connects `ai/drAIs`.

Repository adapter:

- [`drAIs/`](drAIs/README.md)

drAIs remains authoritative for the local assistant runtime, coordination,
context construction, skills, model-provider adapters, sandbox policy,
security, and evaluation. HoloBike Deployment selects a compatible runtime,
skillset, model profile, and product-facing bridge, then validates that its
declared tools and services are available in the assembled environment.

The deployment boundary should cover:

- runtime, protocol, and configuration versions;
- selected skillset and required external capabilities;
- provider and model requirements without secret values;
- uroborOS service dependencies such as Chronosphere;
- product-facing Unreal bridge compatibility;
- sandbox and context-egress policy; and
- evaluation and startup-health evidence.

Development providers and fixtures must be explicit. Production model
credentials and user-derived context never belong in this repository or its
assembly reports.
