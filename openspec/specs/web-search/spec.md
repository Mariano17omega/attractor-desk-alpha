# web-search Specification

## Purpose
TBD - created by archiving change add-web-search-summarization-title. Update Purpose after archive.
## Requirements
### Requirement: Web Search Classification
The system SHALL decide whether to run a web search for the latest user message when deep search is enabled, using an LLM classifier configured for deterministic output.

#### Scenario: Message does not require search
- **WHEN** deep search is enabled and the classifier returns false
- **THEN** the system SHALL skip web search and proceed without web results.

### Requirement: Web Search Query Generation
The system SHALL generate a search-friendly query from recent conversation context when web search is required.

#### Scenario: Query generated from conversation
- **WHEN** the classifier indicates a web search is needed
- **THEN** the system SHALL generate a query that preserves the user's intent and includes current date context.

### Requirement: Web Search Results Injection
The system SHALL execute a web search (default Exa) using the generated query and inject up to the configured number of results into model context as a hidden message tagged with `__oc_web_search_results_message`.

#### Scenario: Results available
- **WHEN** search returns results
- **THEN** the system SHALL attach results to internal messages and continue the artifact flow.

#### Scenario: No results
- **WHEN** search returns no results or the provider is unavailable
- **THEN** the system SHALL continue the artifact flow without injected results.

