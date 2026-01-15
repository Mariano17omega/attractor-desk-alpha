# Spec: Image Processing

## ADDED Requirements

### Requirement: Dedicated Image Processing Node
The system SHALL route image-related requests to a dedicated `imageProcessing` node, ensuring modular handling of multimodal inputs.

#### Scenario: User requests image analysis
- **Given** the user sends a message containing an image and a question about it
- **When** the message is processed by the graph
- **Then** the system should route the request to the `imageProcessing` node
- **And** the node should use the configured `image_model` to generate a response

### Requirement: Model Configuration for Image Processing
The system SHALL support configuration of a specific AI model for the `imageProcessing` node, distinct from the default model used for text-only tasks.

#### Scenario: Configuration of image model
- **Given** the system configuration
- **When** the `image_model` parameter is set (e.g., to "gpt-4o")
- **Then** the `imageProcessing` node should use this specific model
- **And** other nodes should continue using the default `model`

#### Scenario: Fallback behavior
- **Given** no specific `image_model` is configured
- **When** the `imageProcessing` node is invoked
- **Then** it should fallback to a sensible default (e.g., the main `model` or a hardcoded multimodal capable model)
