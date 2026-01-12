## ADDED Requirements
### Requirement: Conversation Summarization
The system SHALL summarize internal messages when the message character budget exceeds the summarization threshold and replace internal history with a summary message tagged by `__oc_summarized_message`.

#### Scenario: Summary triggered
- **WHEN** internal messages exceed the character budget
- **THEN** the system SHALL create a summary message, mark it with `__oc_summarized_message`, and store it only in internal messages.
