import os
import networkx as nx
from pyvis.network import Network
from typing import List, Optional
import webbrowser
import tempfile

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document 
from dotenv import load_dotenv

load_dotenv()


# --- 1. Define Pydantic Schema for Structured Output ---

class KnowledgeTriple(BaseModel):
    """A single triple representing a knowledge relationship."""
    subject: str = Field(description="The entity (noun/proper noun) performing the action or being described.")
    predicate: str = Field(description="The verb or phrase that describes the relationship between the subject and the object.")
    object: str = Field(description="The entity (noun/proper noun) that is the target of the relationship or description.")

class KnowledgeGraphSchema(BaseModel):
    """A container for the list of knowledge triples extracted from the text."""
    triples: List[KnowledgeTriple]

# --- 2. Main Logic Function ---

def generate_knowledge_graph(docs: List[Document], html_filepath: str = "knowledge_graph.html") -> int:
    """
    Generates an interactive knowledge graph from a list of Document objects using 
    Gemini, NetworkX, and Pyvis, and saves it as an HTML file.

    Args:
        docs: A list of Document objects containing the text content.
        html_filepath: The path to save the generated HTML file.
    """
    print("Starting Knowledge Graph generation from Document list...")

    # Combine all document contents into a single string for the LLM
    text_input = " ".join([doc.page_content for doc in docs])
    
    if not text_input.strip():
        print("ERROR: Input documents contained no readable text content.")
        return

    # Configuration and Initialization
    # NOTE: Ensure the GOOGLE_API_KEY environment variable is set.
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY environment variable is not set. Cannot proceed with LLM call.")
        return

    # 1. Initialize LLM with structured output
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=api_key,
            temperature=0.1
        )
        
        # Use with_structured_output to force the model to return JSON matching the schema
        structured_llm = llm.with_structured_output(KnowledgeGraphSchema)
        
        # Define the system instruction and user prompt
        system_instruction = (
            "You are an expert knowledge graph extractor. "
            "Your task is to analyze the provided text and extract a list of "
            "accurate Subject-Predicate-Object triples. The output MUST be a JSON "
            "object that strictly adheres to the provided schema. "
            "Identify the most important entities and their direct relationships."
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            ("human", "Extract knowledge triples from the following text:\n\n{text}"),
        ])

        # Chain the prompt and the LLM
        kg_chain = prompt | structured_llm

        print("Calling Gemini model to extract triples...")
        response_data = kg_chain.invoke({"text": text_input})
        
    except Exception as e:
        print(f"An error occurred during LLM invocation: {e}")
        return

    # 2. Extract Triples
    if not response_data or not isinstance(response_data, KnowledgeGraphSchema):
        print("ERROR: Failed to parse structured output from the LLM.")
        return

    triples = response_data.triples
    if not triples:
        print("No knowledge triples were extracted by the model.")
        return

    print(f"Successfully extracted {len(triples)} triples.")
    
    # 3. Build the NetworkX Graph
    graph = nx.DiGraph()
    for triple in triples:
        subject = triple.subject.strip()
        predicate = triple.predicate.strip()
        obj = triple.object.strip()

        # Add nodes
        graph.add_node(subject, title=subject, group='subject')
        graph.add_node(obj, title=obj, group='object')

        # Add edge (relationship)
        # Use the predicate as the edge label
        graph.add_edge(subject, obj, title=predicate, label=predicate)

    # 4. Convert to Pyvis Network for visualization
    # Note: notebook=False ensures it's configured for a standalone HTML file
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", notebook=False)
    net.toggle_physics(True) 
    
    # Transfer the NetworkX graph to the Pyvis network
    net.from_nx(graph)

    # Customize the visualization (optional but recommended)
    net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -10000,
              "centralGravity": 0.3,
              "springLength": 100,
              "damping": 0.9,
              "avoidOverlap": 0.5
            },
            "minVelocity": 0.75
          },
          "nodes": {
            "font": {
              "size": 18,
              "face": "Inter",
              "color": "white"
            },
            "shape": "dot",
            "size": 25,
            "color": {
                "border": "#FFFFFF", 
                "background": "#FF9900"
            }
          },
          "edges": {
            "font": {
                "color": "#DDDDDD",
                "size": 12,
                "face": "Inter",
                "strokeWidth": 0
            },
            "color": {
                "color": "#555555",
                "highlight": "#FFD700"
            },
            "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } }
          }
        }
    """)
    
    # 5. Save the HTML file with the number of triples in a comment
    net.save_graph(html_filepath)
    
    # Add professional styling and header to the HTML file
    with open(html_filepath, 'r+', encoding='utf-8') as f:
        content = f.read()
        
        # Extract the head content (scripts and styles from pyvis)
        import re
        head_match = re.search(r'<head>(.*?)</head>', content, re.DOTALL)
        body_match = re.search(r'<body>(.*?)</body>', content, re.DOTALL)
        
        if head_match and body_match:
            original_head = head_match.group(1)
            original_body = body_match.group(1)
            
            # Enhanced HTML with professional styling
            styled_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph Visualization</title>
    {original_head}
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
            color: #2c3e50;
            min-height: 100vh;
            overflow-x: hidden;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
            padding: 1.5rem 2rem;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.05);
        }}
        
        .header-content {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .title-section {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .icon {{
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #FF9900 0%, #FFB84D 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 15px rgba(255, 153, 0, 0.3);
        }}
        
        h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stats {{
            display: flex;
            gap: 2rem;
            align-items: center;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0.5rem 1.5rem;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 10px;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }}
        
        .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #FF9900;
        }}
        
        .stat-label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #7f8c8d;
            margin-top: 0.25rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .graph-container {{
            background: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
        }}
        
        .controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }}
        
        .btn {{
            padding: 0.75rem 1.5rem;
            background: rgba(255, 153, 0, 0.1);
            border: 1px solid #FF9900;
            border-radius: 8px;
            color: #FF9900;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
            font-family: 'Inter', sans-serif;
        }}
        
        .btn:hover {{
            background: #FF9900;
            color: #ffffff;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 153, 0, 0.3);
        }}
        
        .info-panel {{
            background: rgba(255, 255, 255, 0.9);
            border-radius: 15px;
            padding: 1.5rem;
            border: 1px solid rgba(0, 0, 0, 0.08);
        }}
        
        .info-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #2c3e50;
        }}
        
        .info-text {{
            color: #5a6c7d;
            line-height: 1.6;
            font-size: 0.9rem;
        }}
        
        .legend {{
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid #2c3e50;
        }}
        
        .legend-label {{
            font-size: 0.85rem;
            color: #5a6c7d;
        }}
        
        #mynetwork {{
            border-radius: 10px;
            overflow: hidden;
            width: 100% !important;
            height: 750px !important;
        }}
        
        .card {{
            background: transparent !important;
            border: none !important;
        }}
        
        .card-body {{
            padding: 0 !important;
        }}
        
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                align-items: flex-start;
            }}
            
            .stats {{
                width: 100%;
                justify-content: space-between;
            }}
            
            h1 {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <!-- Triples extracted: {len(triples)} -->
    
    <div class="header">
        <div class="header-content">
            <div class="title-section">
                <div class="icon">🧠</div>
                <h1>Knowledge Graph Visualization</h1>
            </div>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{len(triples)}</div>
                    <div class="stat-label">Triples</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(graph.nodes())}</div>
                    <div class="stat-label">Nodes</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(graph.edges())}</div>
                    <div class="stat-label">Edges</div>
                </div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="graph-container">
            <div class="controls">
                <button class="btn" onclick="network.fit()">🎯 Fit to Screen</button>
                <button class="btn" onclick="network.stabilize()">⚡ Stabilize</button>
                <button class="btn" onclick="togglePhysics()">🔄 Toggle Physics</button>
            </div>
            {original_body}
        </div>
        
        <div class="info-panel">
            <div class="info-title">📊 Graph Information</div>
            <div class="info-text">
                This interactive knowledge graph visualizes relationships extracted from your documents. 
                You can drag nodes, zoom in/out, and click on nodes and edges to explore the connections.
            </div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF9900;"></div>
                    <div class="legend-label">Entity Nodes</div>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #555555; border-radius: 0; width: 30px; height: 3px;"></div>
                    <div class="legend-label">Relationships</div>
                </div>
            </div>
        </div>
    </div>
    
    <script type="text/javascript">
        let physicsEnabled = true;
        
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
    </script>
</body>
</html>"""
            
            f.seek(0)
            f.truncate()
            f.write(styled_html)
        else:
            # Fallback: just add the comment if regex fails
            f.seek(0, 0)
            f.write(f"<!-- Triples extracted: {len(triples)} -->\n" + content)
    
    print(f"Successfully generated and saved knowledge graph with {len(triples)} triples to: {html_filepath}")
    return len(triples)


# --- 3. Example Usage ---

if __name__ == "__main__":
    # Example documents, simulating chunking or retrieval
    doc_chunk_1 = Document(page_content=(
        "Artificial Intelligence, often abbreviated as AI, is a field of computer "
        "science focused on creating systems that can perform tasks normally requiring "
        "human intelligence. Machine Learning is a subset of AI."
    ), metadata={"source": "Intro_to_AI.pdf", "page": 1})

    doc_chunk_2 = Document(page_content=(
        "Deep Learning is a specialized area within Machine Learning that uses "
        "neural networks with many layers (deep neural networks). TensorFlow is "
        "a popular framework for Deep Learning, developed by Google."
    ), metadata={"source": "Intro_to_AI.pdf", "page": 2})

    example_documents = [doc_chunk_1, doc_chunk_2]
    
    # Execute the function
    generate_knowledge_graph(
        docs=example_documents,
        html_filepath="ai_knowledge_kg.html"
    )

    print("\nTo view the graph, open 'ai_knowledge_kg.html' in your web browser.")


def create_and_open_knowledge_graph(documents: List[Document], st_progress=None) -> bool:
    """
    Creates a knowledge graph from the provided documents and opens it in the default web browser.
    
    Args:
        documents: List of Document objects containing the text content for graph generation.
        st_progress: Optional Streamlit object for showing progress (used in Streamlit apps).
        
    Returns:
        bool: True if the graph was successfully generated and opened, False otherwise.
    """
    if st_progress:
        status = st_progress.status("🔄 Extracting knowledge triples from documents...")
    
    try:
        # Create a temporary file to store the HTML
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp_file:
            html_path = tmp_file.name
        
        # Generate the knowledge graph
        if st_progress:
            status.update(label="🔄 Extracting knowledge triples from documents...")
        
        # Call the generate_knowledge_graph function and capture the number of triples
        generate_knowledge_graph(docs=documents, html_filepath=html_path)
        
        # Get the number of triples from the generated graph
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract the number of triples from the generated HTML
                # This assumes the generate_knowledge_graph function adds a comment with the count
                import re
                match = re.search(r'<!-- Triples extracted: (\d+) -->', content)
                num_triples = int(match.group(1)) if match else 0
        except Exception as e:
            num_triples = 0
        
        if st_progress:
            if num_triples > 0:
                status.update(label=f"✅ Successfully extracted {num_triples} knowledge triples! Opening graph...", state="complete")
            else:
                status.update(label="⚠️ Generated knowledge graph (could not determine number of triples)", state="complete")
        
        # Open in default browser
        webbrowser.open(f'file://{os.path.abspath(html_path)}')
        return True
        
    except Exception as e:
        error_msg = f"Error creating/opening knowledge graph: {e}"
        if st_progress:
            status.update(label=f"❌ {error_msg}", state="error")
        else:
            print(error_msg)
        # Clean up the temporary file if it was created
        if 'html_path' in locals() and os.path.exists(html_path):
            os.unlink(html_path)
        return False
 