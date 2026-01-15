# Image Processing Node

## Goal Description
Create a dedicated image processing node in the Open Canvas graph responsible solely for image-related operations. This node will support selecting a specific AI model (e.g., multimodal models) distinct from the default text-only model used by other system components. This ensures modular architecture and allows for optimized models for different tasks.

## User Review Required
> [!IMPORTANT]
> This change introduces a new configuration parameter `image_model` for the graph execution. Clients invoking the graph will need to provide this parameter if they wish to use a custom model for image processing; otherwise, a default will be used.

## Proposed Changes

### Core Graph
#### [MODIFY] [graph.py](file:///home/m/Projetos/Projetos/attractor-desk-alpha/core/graphs/open_canvas/graph.py)
- Register `imageProcessing` node.
- Add conditional edges to route to `imageProcessing` from `generatePath` (or relevant router).
- Add edge from `imageProcessing` to `generateFollowup` (or `cleanState` depending on flow).

#### [MODIFY] [generate_path.py](file:///home/m/Projetos/Projetos/attractor-desk-alpha/core/graphs/open_canvas/nodes/generate_path.py)
- Update routing logic/prompt to detect image-related intents and route to `imageProcessing`.

### Nodes
#### [NEW] [image_processing.py](file:///home/m/Projetos/Projetos/attractor-desk-alpha/core/graphs/open_canvas/nodes/image_processing.py)
- Implement `image_processing` node function.
- Retrieve `image_model` from `config["configurable"]`.
- Invoke the multimodal model with image content.

### Configuration
#### [MODIFY] [state.py](file:///home/m/Projetos/Projetos/attractor-desk-alpha/core/graphs/open_canvas/state.py)
- Update state definition if necessary (unlikely if just using messages, but check if we need to store image intermediates).

## Verification Plan

### Automated Tests
- Unit test for `image_processing` node:
    - Mock `get_chat_model` and `ainvoke`.
    - Verify correct model name is used from config.
    - Verify image content is processed.
- Integration test for `graph`:
    - Simulate a user message requesting image analysis.
    - Verify routing to `imageProcessing`.

### Manual Verification
- Start the application.
- Configure `image_model` (if UI exposure is added, otherwise just verify backend logs/default).
- Upload an image and ask a question about it.
- Verify that the `imageProcessing` node handles the request and the response is accurate.
