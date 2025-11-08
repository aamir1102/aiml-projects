import os
import streamlit as st
from streamlit_chat import message
import base64
from io import BytesIO
from PIL import Image
import tempfile
from pyvis.network import Network
import streamlit.components.v1 as components
from streamlit_option_menu import option_menu
from streamlit_extras.stylable_container import stylable_container
import requests
from bs4 import BeautifulSoup

# Import backend services
from backend_services import (
    image_to_base64,
    extract_text_from_file,
    extract_text_from_url,
    generate_knowledge_graph,
    text_to_speech,
    get_mock_response,
    process_documents,
    summarize_documents
)

# Load and encode avatars
USER_AVATAR = f"data:image/jpeg;base64,{image_to_base64('PHOTO.jpg')}" if os.path.exists('PHOTO.jpg') else ""
BOT_AVATAR = f"data:image/jpeg;base64,{image_to_base64('openai-logo.jpg')}" if os.path.exists('openai-logo.jpg') else ""

# Page configuration
st.set_page_config(
    page_title="Knowledge Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    
    /* Chat message styling */
    .chat-container {
        margin: 15px 0;
    }
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
    }
    .bot-message {
        display: flex;
        margin-bottom: 15px;
    }
    .message-bubble {
        max-width: 70%;
        padding: 10px 15px;
        border-radius: 18px;
        line-height: 1.4;
    }
    .user-bubble {
        background: #e3f2fd;
        margin-left: 10px;
    }
    .bot-bubble {
        background: #f0f2f6;
        margin-right: 10px;
    }
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
    }
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .stTextInput>div>div>input {
        border-radius: 20px;
        padding: 10px 15px;
    }
    .stFileUploader>div>div {
        border: 2px dashed #4CAF50;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre;
        background-color: #f0f2f6;
        border-radius: 10px 10px 0 0;
        gap: 1px;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    .summary-box {
        background-color: #e8f5e9;
        border-left: 5px solid #4CAF50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
        max-height: 300px;
        overflow-y: auto;
        word-wrap: break-word;
    }
    .audio-player {
        width: 100%;
        margin: 1rem 0;
    }
    """, unsafe_allow_html=True)
# Initialize session state
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []
if 'websites' not in st.session_state:
    st.session_state['websites'] = []
if 'summary' not in st.session_state:
    st.session_state['summary'] = ""
if 'documents_processed' not in st.session_state:
    st.session_state['documents_processed'] = False
if 'processing_status' not in st.session_state:
    st.session_state['processing_status'] = ""

# Core application logic remains in app.py
# Backend services have been moved to backend_services.py

# Main App
def main():
    st.title("🤖 Knowledge Assistant")
    st.markdown("---")
    
    # Sidebar for document and website management
    with st.sidebar:
        st.header("📚 Knowledge Sources")
        
        # Document uploader
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, DOCX, PPTX, Images)",
            type=['pdf', 'docx', 'pptx', 'jpg', 'jpeg', 'png'],
            accept_multiple_files=True
        )
        
        # Website input
        with st.form("website_form"):
            website_url = st.text_input("Add a website URL:", placeholder="https://example.com")
            add_website = st.form_submit_button("Add Website")
            
            if add_website and website_url:
                if website_url not in st.session_state.websites:
                    st.session_state.websites.append(website_url)
                    st.success(f"Added website: {website_url}")
                else:
                    st.warning("This website has already been added.")
        
        # Display added documents and websites
        st.subheader("📂 Added Sources")
        
        if uploaded_files:
            st.write("**Documents:**")
            for file in uploaded_files:
                st.caption(f"📄 {file.name}")
        
        if st.session_state.websites:
            st.write("**Websites:**")
            for url in st.session_state.websites:
                st.caption(f"🌐 {url}")
        
        # Add a button to process documents
        st.markdown("---")
        st.subheader("⚙️ Document Processing")
        
        # Show processing status if available
        if st.session_state.processing_status:
            st.info(st.session_state.processing_status)
        
        # Process Documents button
        if st.button("🔍 Process Documents", use_container_width=True, 
                    disabled=not (uploaded_files or st.session_state.websites)):
            if uploaded_files or st.session_state.websites:
                with st.spinner("Processing documents. This may take a few moments..."):
                    success, message, _ = process_documents(
                        uploaded_files, 
                        st.session_state.websites if st.session_state.websites else None
                    )
                    
                    if success:
                        st.session_state.documents_processed = True
                        st.session_state.processing_status = message
                        st.rerun()
                    else:
                        st.error(f"Error: {message}")
            else:
                st.warning("Please upload documents or add website URLs first.")
        
        # Add a button to open the knowledge graph HTML
        st.markdown("---")
        st.subheader("🧠 Knowledge Graph")
        if st.button("Open Knowledge Graph", use_container_width=True, 
                    disabled=not st.session_state.documents_processed):
            import webbrowser
            import os
            # Get the absolute path to the HTML file
            html_path = os.path.abspath("knowledge_graph.html")
            # Open in default browser
            webbrowser.open(f'file://{html_path}')
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat interface
        st.subheader("💬 Chat with your documents")
        
        # Chat input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area("Ask a question about your documents:", height=100, 
                                   placeholder="Type your question here...", key="user_input")
            submit_button = st.form_submit_button("Send")
        
        # Process form submission
        if submit_button and user_input:
            # Add user message to chat history
            st.session_state.past.append(user_input)
            
            # Generate response
            with st.spinner("Analyzing your question..."):
                # Pass the database if it exists in session state
                db = st.session_state.get('vector_db', None)
                response = get_mock_response(user_input, db=db)
                st.session_state.generated.append(response)
        
        # Display chat history (newest conversations at the top)
        if st.session_state['generated']:
            # Get the total number of message pairs
            num_pairs = len(st.session_state['generated'])
            
            # Display message pairs in reverse order (newest first)
            for i in reversed(range(num_pairs)):
                # Create a container for each conversation pair
                with st.container():
                    # User message with custom avatar
                    st.markdown(f"""
                    <div style="display: flex; margin-bottom: 15px; justify-content: flex-end;">
                        <div style="background: #e3f2fd; padding: 10px 15px; border-radius: 18px; max-width: 80%;">
                            {st.session_state['past'][i]}
                        </div>
                        <img src="{USER_AVATAR}" style="width: 40px; height: 40px; border-radius: 50%; margin-left: 10px; object-fit: cover;">
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Bot response with custom avatar
                    bot_response = st.session_state["generated"][i]
                    st.markdown(f"""
                    <div style="display: flex; margin-bottom: 15px;">
                        <img src="{BOT_AVATAR}" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 10px; object-fit: cover;">
                        <div style="background: #f0f2f6; padding: 10px 15px; border-radius: 18px; max-width: 80%;">
                            {bot_response}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Audio generation has been removed as requested
                    # Add some spacing between conversation pairs
                    st.markdown("<div style='margin: 15px 0;'></div>", unsafe_allow_html=True)
    
    with col2:
        st.subheader("🔍 Actions")
        
        # Display summary if it exists in session state
        if 'summary' in st.session_state and st.session_state['summary']:
            with st.expander("📄 Document Summary", expanded=True):
                st.markdown(f"<div class='summary-box'>{st.session_state['summary']}</div>", unsafe_allow_html=True)
                
                # Add a button to generate audio
                if st.button("🔊 Generate Audio", key="generate_audio_btn"):
                    with st.spinner("Generating audio... This may take a moment..."):
                        audio_data = text_to_speech(st.session_state['summary'])
                        if audio_data:
                            st.session_state['audio_base64'] = audio_data
                            st.session_state['audio_available'] = True
                            st.session_state['last_summary'] = st.session_state['summary']
                            st.success("Audio generated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to generate audio. Please try again.")
                
                # Display audio player if we have audio data and the summary hasn't changed
                if (st.session_state.get('audio_available', False) and 
                    'audio_base64' in st.session_state and 
                    st.session_state.get('last_summary') == st.session_state['summary']):
                    try:
                        audio_base64 = st.session_state['audio_base64']
                        audio_html = f"""
                        <div style="margin: 10px 0;">
                            <audio controls class="audio-player" style="width: 100%;">
                                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                                Your browser does not support the audio element.
                            </audio>
                        </div>
                        """
                        st.markdown(audio_html, unsafe_allow_html=True)
                        
                        # Single download button
                        st.download_button(
                            label="Download Audio",
                            data=base64.b64decode(audio_base64),
                            file_name="summary.mp3",
                            mime="audio/mp3",
                            key="summary_audio_download"
                        )
                    except Exception as e:
                        st.warning("Could not load audio player. Please try generating the audio again.")
                        st.session_state['audio_available'] = False
        
        # Summarize button
        if st.button("📝 Summarize Documents", use_container_width=True):
            all_docs = []
            
            # Process uploaded files
            if uploaded_files:
                for file in uploaded_files:
                    docs = extract_text_from_file(file)
                    if docs:
                        all_docs.extend(docs)
            
            # Process websites
            if st.session_state.websites:
                for url in st.session_state.websites:
                    docs = extract_text_from_url(url)
                    if docs:
                        all_docs.extend(docs)
            
            if all_docs:
                with st.spinner("Generating summary... This may take a moment..."):
                    try:
                        # Use the new summarize_documents function
                        summary = summarize_documents(all_docs)
                        st.session_state['summary'] = summary
                        
                        # Display summary
                        with st.expander("📄 Document Summary", expanded=True):
                            st.markdown(f"<div class='summary-box'>{summary}</div>", unsafe_allow_html=True)
                            
                            # Clear any existing audio when generating a new summary
                            st.session_state['audio_available'] = False
                            st.session_state['last_summary'] = summary
                            
                            # Show button to generate audio
                            if st.button("🔊 Generate Audio", key="new_generate_audio_btn"):
                                with st.spinner("Generating audio... This may take a moment..."):
                                    audio_data = text_to_speech(summary)
                                    if audio_data:
                                        st.session_state['audio_base64'] = audio_data
                                        st.session_state['audio_available'] = True
                                        st.session_state['last_summary'] = summary
                                        st.rerun()
                                    else:
                                        st.error("Failed to generate audio. Please try again.")
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")
                        st.session_state['summary'] = ""
            else:
                st.warning("Please upload documents or add websites first.")
            
            # Generate knowledge graph button
            if st.button("🌐 Generate Knowledge Graph", use_container_width=True, 
                       disabled=not (uploaded_files or st.session_state.websites)):
                with st.spinner("Generating knowledge graph..."):
                    all_docs = []
                    
                    # Process uploaded files
                    if uploaded_files:
                        for file in uploaded_files:
                            docs = extract_text_from_file(file)
                            if docs:
                                all_docs.extend(docs)
                    
                    # Process websites
                    if st.session_state.websites:
                        for url in st.session_state.websites:
                            docs = extract_text_from_url(url)
                            if docs:
                                all_docs.extend(docs)
                    
                    if all_docs:
                        all_texts = [doc.page_content for doc in all_docs if hasattr(doc, 'page_content')]
                        graph_html = generate_knowledge_graph(all_texts)
                        
                        # Save to a temporary HTML file and open in a new tab
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
                        temp_file.write(graph_html)
                        temp_file.close()
                        
                        # Open in a new tab
                        st.markdown(f"""
                        <a href="{temp_file.name}" target="_blank">
                            <button style="width: 100%; padding: 0.5rem; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                Open Knowledge Graph in New Tab
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
            else:
                st.warning("Please upload documents or add websites first.")

if __name__ == "__main__":
    main()
