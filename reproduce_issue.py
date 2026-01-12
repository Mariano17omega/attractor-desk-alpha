
import asyncio
from langchain_core.messages import HumanMessage
from core.graphs.open_canvas.state import OpenCanvasState
from core.types import ArtifactV3, ArtifactMarkdownV3
from core.graphs.open_canvas.nodes.generate_path import generate_path

async def test_routing():
    print("--- Testing Routing ---")
    
    # 1. Setup State with an existing artifact
    initial_artifact = ArtifactV3(
        currentIndex=1,
        contents=[
            ArtifactMarkdownV3(
                index=1,
                title="Test Artifact",
                fullMarkdown="This is the first paragraph.\n\nThis is the second paragraph."
            )
        ]
    )
    
    state = OpenCanvasState(
        messages=[
            HumanMessage(content="Write a short story about a cat.")
        ],
        internal_messages=[
             HumanMessage(content="Write a short story about a cat.")
        ],
        artifact=initial_artifact
    )
    
    # 2. User requests a modification
    modification_request = "Change the first paragraph to say 'The cat sat on the mat'."
    state.messages.append(HumanMessage(content=modification_request))
    state.internal_messages.append(HumanMessage(content=modification_request))
    
    # 3. Invoke generate_path
    config = {"configurable": {"model": "anthropic/claude-3.5-sonnet"}}
    
    try:
        result = await generate_path(state, config)
        print(f"Routing result for '{modification_request}': {result}")
        
        if result.get("next") == "rewriteArtifact":
            print("SUCCESS: Routed to rewriteArtifact")
        else:
            print(f"FAILURE: Routed to {result.get('next')} instead of rewriteArtifact")
            
    except Exception as e:
        print(f"Error during routing: {e}")

if __name__ == "__main__":
    asyncio.run(test_routing())
