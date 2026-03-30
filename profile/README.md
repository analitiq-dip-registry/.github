# Analitiq Data Integration Protocol Registry

**If APIs and databases have standard interfaces, why can't we use AI to standardise how they talk to each other?**

That's the question behind this project. Every API publishes documentation. Every database speaks SQL. The patterns are consistent -- authentication, pagination, filtering, schema discovery. Yet connecting systems still requires custom code, brittle scripts, and deep technical knowledge.

We're building an open registry of **Data Integration Protocols (DIPs)** -- machine-readable connector definitions that describe how to authenticate with a system, what data is available, and how to move it. These protocols are created and maintained using Claude, and validated by human contributors to research APIs, map data schemas, and produce standardised definitions that a data integration platform can consume.

## Our goal
We want to make it easier for anyone to connect their systems, to create a connection to **any** API or database within minutes using Claude code.

## How It Works

Claude plugin reads API documentation, database specs, and system references, then generates structured connector definitions following a strict protocol format. The result is a universal language for data movement -- no custom code, no vendor lock-in, no technical expertise required.

Each connector in this registry is a complete protocol definition:
- **Authentication** -- how to connect (OAuth2, API keys, database credentials, SSH tunnels)
- **Endpoints** -- what data is available and how to query it (API connectors)
- **Schema discovery** -- runtime detection of tables and fields (database connectors)
- **Filters, pagination, rate limits** -- the operational details that make integrations reliable

## Browse Connectors

All connectors are listed as repositories in this organisation. The full registry is also available as machine-readable JSON:

```
https://raw.githubusercontent.com/analitiq-dip-registry/.github/main/registry.json
```

## Using Connectors

### Analitiq Cloud

A cloud version with all the enterprise bells and whistles is on [analitiq-app.com](https://analitiq-app.com). Select a source and destination, and the platform handles the rest.

### Open Source

1. Clone the [analitiq-core](https://github.com/analitiq-core) repository
2. Install the Claude plugin `analitiq-plugin-dataflow`
3. Launch Claude and say: *"I need to move data from X to Y"*

The plugin fetches the required connectors from this registry and sets up the pipeline automatically.

## Creating New Connectors

Anyone can create a connector -- no programming required. Claude does the research, generates the protocol definition, and validates the result.

```
claude plugin add analitiq-ai/ai-plugins-official
```

Then say: *"I want to create a connector for [system name]"*

Claude will research the system's documentation, determine authentication methods, map available endpoints, and produce a complete, standardised connector definition.

## Contributing

This registry is community-maintained. See [CONTRIBUTING.md](https://github.com/analitiq-dip-registry/template/blob/main/CONTRIBUTING.md) for guidelines.

## Links

- [Analitiq Cloud](https://analitiq-app.com) -- managed platform for running data integrations in the cloud
- [AI Plugins](https://github.com/analitiq-ai/ai-plugins-official) -- open-source Claude Code plugins for building connectors and data pipelines
- [Connector Template](https://github.com/analitiq-dip-registry/template) -- starting point for new connector definitions