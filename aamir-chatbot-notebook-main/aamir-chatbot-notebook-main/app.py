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
    summarize_documents,
    get_tavily_search_response
)

# Avatars removed as per user request

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
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Root Variables */
    :root {
        --primary-color: #6366f1;
        --primary-dark: #4f46e5;
        --primary-light: #818cf8;
        --secondary-color: #8b5cf6;
        --success-color: #10b981;
        --background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --card-bg: rgba(255, 255, 255, 0.98);
        --text-primary: #1f2937;
        --text-secondary: #6b7280;
        --border-color: #e5e7eb;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
    }
    
    /* Header Styling */
    h1 {
        font-weight: 700 !important;
        font-size: 2.5rem !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
        letter-spacing: -0.02em;
    }
    
    h2, h3 {
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 1px solid var(--border-color);
        box-shadow: var(--shadow-lg);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 2rem;
    }
    
    /* Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: var(--shadow-md) !important;
        width: 100%;
        letter-spacing: 0.01em;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-xl) !important;
        background: linear-gradient(135deg, var(--primary-dark) 0%, #7c3aed 100%) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    .stButton > button:disabled {
        background: #d1d5db !important;
        color: #9ca3af !important;
        cursor: not-allowed !important;
        transform: none !important;
        box-shadow: none !important;
    }
    
    /* Text Input Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 12px !important;
        border: 2px solid var(--border-color) !important;
        padding: 0.875rem 1.25rem !important;
        font-size: 0.95rem !important;
        transition: all 0.3s ease !important;
        background-color: white !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
        outline: none !important;
    }
    
    /* File Uploader Styling */
    .stFileUploader > div {
        border: 2px dashed var(--primary-light) !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        text-align: center !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%) !important;
        transition: all 0.3s ease !important;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--primary-color) !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%) !important;
        transform: translateY(-2px);
        box-shadow: var(--shadow-md) !important;
    }
    
    /* Chat Message Styling */
    .chat-container {
        margin: 0;
    }
    
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 16px;
        margin-top: 0;
        animation: slideInRight 0.3s ease-out;
    }
    
    .bot-message {
        display: flex;
        margin-bottom: 16px;
        margin-top: 0;
        animation: slideInLeft 0.3s ease-out;
    }
    
    /* Remove extra spacing from first message */
    .user-message:first-child,
    .bot-message:first-child {
        margin-top: 0 !important;
    }
    
    /* Remove extra spacing in chat history area */
    [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    
    /* Ensure chat messages start at top of container */
    .element-container:has(.user-message),
    .element-container:has(.bot-message) {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Remove spacing between markdown elements in chat */
    [data-testid="stMarkdownContainer"] + [data-testid="stMarkdownContainer"] {
        margin-top: 0 !important;
    }
    
    /* Ensure first markdown in chat container has no top margin */
    .element-container:has([class*="chat"]) > [data-testid="stMarkdownContainer"]:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .message-bubble {
        max-width: 75%;
        padding: 14px 18px;
        border-radius: 20px;
        line-height: 1.6;
        font-size: 0.95rem;
        box-shadow: var(--shadow-md);
        word-wrap: break-word;
    }
    
    .user-bubble {
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        color: #111827;
        border: 1px solid #e5e7eb;
        border-bottom-right-radius: 4px;
        margin-left: 10px;
    }
    
    .bot-bubble {
        background: white;
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-bottom-left-radius: 4px;
        margin-right: 10px;
        box-shadow: var(--shadow-sm);
    }
    
    /* Summary Box Styling */
    .summary-box {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
        border-left: 4px solid var(--primary-color);
        padding: 1.25rem;
        border-radius: 12px;
        margin: 1rem 0;
        max-height: 400px;
        overflow-y: auto;
        word-wrap: break-word;
        box-shadow: var(--shadow-sm);
        font-size: 0.95rem;
        line-height: 1.7;
        color: var(--text-primary);
    }
    
    .summary-box::-webkit-scrollbar {
        width: 6px;
    }
    
    .summary-box::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .summary-box::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 10px;
    }
    
    .summary-box::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        background: white !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.3s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        box-shadow: var(--shadow-md) !important;
        border-color: var(--primary-light) !important;
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
        border-bottom: 2px solid var(--border-color);
        padding-bottom: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre;
        background-color: transparent;
        border-radius: 12px 12px 0 0;
        padding: 0 24px;
        font-weight: 500;
        color: var(--text-secondary);
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(99, 102, 241, 0.1);
        color: var(--primary-color);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        color: white;
        box-shadow: var(--shadow-md);
    }
    
    /* Audio Player Styling */
    .audio-player {
        width: 100%;
        margin: 1rem 0;
        border-radius: 12px;
    }
    
    audio {
        border-radius: 12px;
        filter: drop-shadow(var(--shadow-sm));
    }
    
    /* Checkbox Styling */
    .stCheckbox > label {
        font-weight: 500;
        color: var(--text-primary);
    }
    
    /* Info/Warning/Success Messages */
    .stAlert {
        border-radius: 12px !important;
        border-left: 4px solid !important;
        box-shadow: var(--shadow-sm) !important;
    }
    
    /* Caption Styling */
    .stCaption {
        color: var(--text-secondary);
        font-size: 0.875rem;
        padding: 0.5rem;
        background: rgba(99, 102, 241, 0.05);
        border-radius: 8px;
        margin: 0.25rem 0;
    }
    
    /* Divider Styling */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--border-color), transparent);
        margin: 1.5rem 0;
    }
    
    /* Full-screen Spinner Overlay */
    .spinner-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        /* Make overlay subtle so the UI remains visible */
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.18) 0%, rgba(118, 75, 162, 0.18) 100%);
        backdrop-filter: blur(4px);
        z-index: 999999;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
        /* Allow interacting with the underlying UI while overlay is shown */
        pointer-events: none;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    
    .spinner-modal {
        /* Glassmorphism card for a more professional look */
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px) saturate(120%);
        -webkit-backdrop-filter: blur(10px) saturate(120%);
        border: 1px solid rgba(255, 255, 255, 0.6);
        padding: 2rem 2.5rem;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(31, 41, 55, 0.18);
        text-align: center;
        animation: modalFadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        max-width: 420px;
        /* Keep the modal itself interactive if needed */
        pointer-events: auto;
    }
    
    @keyframes modalFadeIn {
        from {
            opacity: 0;
            transform: scale(0.9) translateY(-20px);
        }
        to {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }
    
    .spinner-circle {
        width: 64px;
        height: 64px;
        margin: 0 auto 24px;
        border: 4px solid rgba(229, 231, 235, 0.8);
        border-top: 4px solid var(--primary-color);
        border-right: 4px solid var(--secondary-color);
        border-radius: 50%;
        animation: spin 0.9s linear infinite;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .spinner-title {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
        letter-spacing: -0.02em;
    }
    
    .spinner-subtitle {
        color: var(--text-secondary);
        font-size: 1rem;
        font-weight: 400;
        line-height: 1.6;
    }
    
    .spinner-dots::after {
        content: '';
        animation: dots 1.5s steps(4, end) infinite;
    }
    
    @keyframes dots {
        0%, 20% { content: ''; }
        40% { content: '.'; }
        60% { content: '..'; }
        80%, 100% { content: '...'; }
    }
    
    /* Form Styling */
    .stForm {
        border: none !important;
        border-radius: 0;
        padding: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    
    /* Remove extra spacing from form elements */
    .stForm > div:first-child {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Ensure no gap between label and form */
    .element-container:has(.stForm) {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* Remove spacing from element-container that wraps form after label */
    label + * .element-container,
    label ~ .element-container {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    .stTextArea {
        margin-top: 0 !important;
    }
    
    .stTextArea > div > div > textarea {
        margin-top: 0 !important;
    }
    
    /* Remove default spacing around textarea container */
    .stTextArea > div {
        margin-top: 0 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Reduce spacing between label and input */
    .stTextArea > label {
        margin-bottom: 0.5rem !important;
        display: none !important;
    }
    
    /* Container Styling */
    .stContainer {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: var(--shadow-sm);
        margin-bottom: 1rem;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, var(--success-color) 0%, #059669 100%) !important;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
    }
    
    /* Selectbox Styling */
    .stSelectbox > div > div {
        border-radius: 12px;
        border: 2px solid var(--border-color);
    }
    
    /* Metric Styling */
    .stMetric {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%);
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }
    
    /* Markdown Styling */
    .stMarkdown {
        color: var(--text-primary);
    }
    
    /* Sidebar Elements */
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: var(--text-primary) !important;
    }
    
    /* Scrollbar Styling for Main Area */
    .main .block-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .main .block-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .main .block-container::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 10px;
    }
    
    .main .block-container::-webkit-scrollbar-thumb:hover {
        background: var(--primary-dark);
    }
    
    /* Additional Polish */
    .element-container {
        transition: all 0.3s ease;
    }
    
    /* Improve spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Better focus states */
    button:focus-visible,
    input:focus-visible,
    textarea:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
    }
    
    /* Smooth page transitions */
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    
    .main .block-container {
        animation: fadeIn 0.5s ease-in;
    }
    
    /* Improve code blocks if any */
    code {
        background: rgba(99, 102, 241, 0.1);
        padding: 0.2em 0.4em;
        border-radius: 4px;
        font-size: 0.9em;
        color: var(--primary-color);
    }
    
    /* Enhance status messages */
    .stSuccess {
        border-left: 4px solid var(--success-color) !important;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%) !important;
    }
    
    .stError {
        border-left: 4px solid #ef4444 !important;
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%) !important;
    }
    
    .stWarning {
        border-left: 4px solid #f59e0b !important;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%) !important;
    }
    
    .stInfo {
        border-left: 4px solid var(--primary-color) !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%) !important;
    }
    </style>
    """, unsafe_allow_html=True)
# Helper function to show spinner overlay
def show_spinner_overlay(title, subtitle):
    spinner_html = f"""
    <div class="spinner-overlay">
        <div class="spinner-modal">
            <div class="spinner-circle"></div>
            <div class="spinner-title">{title}</div>
            <div class="spinner-subtitle spinner-dots">{subtitle}</div>
        </div>
    </div>
    """
    return st.markdown(spinner_html, unsafe_allow_html=True)

# Initialize session state
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []
if 'websites' not in st.session_state:
    st.session_state['websites'] = []
if 'summary' not in st.session_state:
    st.session_state['summary'] = ""
if 'doc_summary' not in st.session_state:
    st.session_state['doc_summary'] = ""
if 'link_summary' not in st.session_state:
    st.session_state['link_summary'] = ""
if 'documents_processed' not in st.session_state:
    st.session_state['documents_processed'] = False
if 'processing_status' not in st.session_state:
    st.session_state['processing_status'] = ""
if 'is_processing' not in st.session_state:
    st.session_state['is_processing'] = False
if 'current_operation' not in st.session_state:
    st.session_state['current_operation'] = None
if 'use_external_search' not in st.session_state:
    st.session_state['use_external_search'] = False

# Core application logic remains in app.py
# Backend services have been moved to backend_services.py

# Main App
def main():
    # Enhanced main title with elegant styling
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0 1.5rem 0; margin-bottom: 2rem;">
        <h1 style="font-size: 3rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; letter-spacing: -0.02em;">🤖 Knowledge Assistant</h1>
        <p style="color: #6b7280; font-size: 1.1rem; font-weight: 400; margin-top: 0.5rem;">Intelligent document analysis and chat interface</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for document and website management with elegant styling
    with st.sidebar:
        st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="font-size: 1.75rem; font-weight: 700; margin-bottom: 0.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">📚 Knowledge Sources</h1>
        </div>
        """, unsafe_allow_html=True)
        
        # Document uploader with enhanced styling
        st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 0.75rem;">📤 Upload Documents</h3>
        </div>
        """, unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, DOCX, PPTX, Images)",
            type=['pdf', 'docx', 'pptx', 'jpg', 'jpeg', 'png'],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Website input with enhanced styling
        st.markdown("""
        <div style="margin-bottom: 1rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 0.75rem;">🌐 Add Website</h3>
        </div>
        """, unsafe_allow_html=True)
        with st.form("website_form"):
            website_url = st.text_input("Add a website URL:", placeholder="https://example.com", label_visibility="collapsed")
            add_website = st.form_submit_button("➕ Add Website", use_container_width=True)
            
            if add_website and website_url:
                if website_url not in st.session_state.websites:
                    st.session_state.websites.append(website_url)
                    st.success(f"✓ Added: {website_url}")
                else:
                    st.warning("⚠️ This website has already been added.")
        
        st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
        
        # Display added documents and websites with enhanced styling
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); padding: 1rem; border-radius: 12px; border: 1px solid #e5e7eb; margin-bottom: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 0.75rem; margin-top: 0;">📂 Added Sources</h3>
        """, unsafe_allow_html=True)
        
        if uploaded_files:
            st.markdown("<div style='margin-bottom: 0.75rem;'><strong style='color: #6366f1; font-size: 0.875rem;'>Documents:</strong></div>", unsafe_allow_html=True)
            for file in uploaded_files:
                st.markdown(f"<div style='padding: 0.5rem; background: white; border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.875rem; color: #374151;'>📄 {file.name}</div>", unsafe_allow_html=True)
        
        if st.session_state.websites:
            st.markdown("<div style='margin-top: 1rem; margin-bottom: 0.75rem;'><strong style='color: #6366f1; font-size: 0.875rem;'>Websites:</strong></div>", unsafe_allow_html=True)
            for url in st.session_state.websites:
                st.markdown(f"<div style='padding: 0.5rem; background: white; border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.875rem; color: #374151;'>🌐 {url}</div>", unsafe_allow_html=True)
        
        if not uploaded_files and not st.session_state.websites:
            st.markdown("<div style='text-align: center; padding: 1rem; color: #9ca3af; font-size: 0.875rem;'>No sources added yet</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Add a button to process documents with enhanced styling
        st.markdown("""
        <div style="margin: 2rem 0 1.5rem 0; border-top: 2px solid #e5e7eb; padding-top: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 1rem;">⚙️ Document Processing</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Show processing status if available
        if st.session_state.processing_status:
            st.info(st.session_state.processing_status)
        
        # Process Documents button
        if st.button("🔍 Process Documents", use_container_width=True, 
                    disabled=not (uploaded_files or st.session_state.websites) or st.session_state.is_processing):
            if uploaded_files or st.session_state.websites:
                st.session_state.is_processing = True
                st.session_state.current_operation = "Processing Documents"
                st.rerun()
            else:
                st.warning("Please upload documents or add website URLs first.")
        
        # Execute processing if flagged
        if st.session_state.is_processing and st.session_state.current_operation == "Processing Documents":
            show_spinner_overlay("Processing Documents", "Analyzing and indexing your documents")
            
            success, message, vector_db = process_documents(
                uploaded_files, 
                st.session_state.websites if st.session_state.websites else None
            )
            
            st.session_state.is_processing = False
            st.session_state.current_operation = None
            
            if success:
                st.session_state.documents_processed = True
                st.session_state.processing_status = message
                st.session_state.vector_db = vector_db
                st.success(message)
            else:
                st.error(f"Error: {message}")
            
            st.rerun()
        
        # Add a button to open the knowledge graph HTML with enhanced styling
        st.markdown("""
        <div style="margin: 2rem 0 1.5rem 0; border-top: 2px solid #e5e7eb; padding-top: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 1rem;">🧠 Knowledge Graph</h3>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🎨 Generate Knowledge Graph", use_container_width=True, 
                    disabled=not st.session_state.documents_processed or st.session_state.is_processing):
            st.session_state.is_processing = True
            st.session_state.current_operation = "Generating Knowledge Graph"
            st.rerun()
        
        # Execute knowledge graph generation if flagged
        if st.session_state.is_processing and st.session_state.current_operation == "Generating Knowledge Graph":
            from graph_creation import create_and_open_knowledge_graph
            
            show_spinner_overlay("Generating Knowledge Graph", "Creating visual representation of your data")
            
            # Get the processed documents from the vector database
            if hasattr(st.session_state, 'vector_db') and st.session_state.vector_db is not None:
                # Get all document chunks from the vector store
                documents = []
                # Get all document IDs from the collection
                collection = st.session_state.vector_db._collection
                if hasattr(collection, 'get'):
                    # ChromaDB specific way to get all documents
                    results = collection.get(include=['documents', 'metadatas'])
                    if results and 'documents' in results:
                        from langchain_core.documents import Document
                        for i, (doc_text, metadata) in enumerate(zip(
                            results['documents'], 
                            results.get('metadatas', [{}] * len(results['documents']))
                        )):
                            documents.append(Document(
                                page_content=doc_text,
                                metadata=metadata or {}
                            ))
                
                if documents:
                    success = create_and_open_knowledge_graph(documents, st_progress=st)
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    
                    if not success:
                        st.error("Failed to generate or open the knowledge graph. Please check the console for details.")
                    else:
                        st.success("Knowledge graph generated successfully!")
                else:
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    st.warning("No document content available to generate knowledge graph.")
            else:
                st.session_state.is_processing = False
                st.session_state.current_operation = None
                st.warning("No processed documents found. Please process your documents first.")
            
            st.rerun()
    
    # Main content area with elegant styling
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([2.2, 1])
    
    with col1:
        # Chat interface with enhanced styling
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 1.5rem;">
            <h2 style="margin: 0; padding-bottom: 0.5rem; border-bottom: 2px solid #e5e7eb;">💬 Chat with your documents</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Add external search toggle
        st.session_state['use_external_search'] = st.checkbox(
            "🌐 Enable External Web Search (Tavily)", 
            value=st.session_state.get('use_external_search', False),
            help="When enabled, the assistant will search the web using Tavily instead of your documents"
        )
        
        # Chat input with enhanced form styling
        placeholder_text = "Search the web..." if st.session_state['use_external_search'] else "Ask a question about your documents..."
        
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "User question",
                height=120, 
                placeholder=placeholder_text, 
                key="user_input",
                label_visibility="collapsed"
            )
            submit_button = st.form_submit_button("📤 Send", use_container_width=True)
        
        # Process form submission
        if submit_button and user_input:
            # Add user message to chat history
            st.session_state.past.append(user_input)
            
            # Generate response based on search mode
            if st.session_state['use_external_search']:
                # Use Tavily external search
                with st.spinner("🔍 Searching the web..."):
                    response = get_tavily_search_response(user_input)
                    st.session_state.generated.append(response)
            else:
                # Use document-based RAG
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
            first_message = True
            for i in reversed(range(num_pairs)):
                # User message with elegant styling
                user_msg = st.session_state['past'][i].replace('"', '&quot;').replace("'", "&#39;")
                top_margin = "margin-top: 0;" if first_message else ""
                st.markdown(f"""
                <div class="user-message" style="{top_margin}">
                    <div class="message-bubble user-bubble">
                        <div style="font-weight: 600; margin-bottom: 6px; font-size: 0.85rem; color: #6b7280; display: flex; align-items: center;">
                            <span style="margin-right: 6px;">🙂</span> You
                        </div>
                        <div style="color: #374151; line-height: 1.7;">{user_msg}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Bot response with elegant styling
                bot_response = st.session_state["generated"][i]
                
                # Handle both string and dictionary responses (for backward compatibility)
                if isinstance(bot_response, dict):
                    response_text = bot_response.get('response', '').replace('"', '&quot;').replace("'", "&#39;")
                    sources = bot_response.get('sources', [])
                else:
                    response_text = bot_response.replace('"', '&quot;').replace("'", "&#39;")
                    sources = []
                
                # Display the response
                st.markdown(f"""
                <div class="bot-message">
                    <div class="message-bubble bot-bubble">
                        <div style="font-weight: 600; margin-bottom: 6px; font-size: 0.85rem; color: #6366f1; display: flex; align-items: center;">
                            <span style="margin-right: 6px;">🤖</span> Assistant
                        </div>
                        <div style="color: #374151; line-height: 1.7;">{response_text}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Display sources if available
                if sources:
                    sources_html = "<div style='margin-top: 12px; padding-top: 12px; border-top: 1px dashed #e5e7eb;'>"
                    sources_html += "<div style='font-size: 0.8rem; color: #6b7280; margin-bottom: 8px; font-weight: 500;'>📚 Sources:</div>"
                    sources_html += "<div style='display: flex; flex-direction: column; gap: 8px;'>"
                    
                    for source in sources:
                        source_name = source.get('source', 'Unknown Source')
                        preview = source.get('page_content', '').replace('"', '&quot;').replace("'", "&#39;")
                        
                        sources_html += f"""
                        <div style='background: #f9fafb; border-radius: 8px; padding: 10px; border: 1px solid #e5e7eb;'>
                            <div style='font-size: 0.8rem; font-weight: 500; color: #4b5563;'>{source_name}</div>
                            <div style='font-size: 0.75rem; color: #6b7280; margin-top: 4px;'>{preview}</div>
                        </div>
                        """
                    
                    sources_html += "</div></div>"
                    st.markdown(sources_html, unsafe_allow_html=True)
                
                # Add elegant divider between conversation pairs
                if i > 0:
                    st.markdown("""
                    <div style="margin: 20px 0; border-top: 1px dashed #e5e7eb;"></div>
                    """, unsafe_allow_html=True)
                
                first_message = False
            
            # end chat history
        else:
            # Empty state with elegant styling (only show when no messages)
            st.markdown("""
            <div style="background: white; padding: 3rem 2rem; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-top: 1.5rem; text-align: center;">
                <div>
                    <div style="font-size: 4rem; margin-bottom: 1rem;">💭</div>
                    <h3 style="color: #6b7280; font-weight: 500; margin-bottom: 0.5rem;">Start a conversation</h3>
                    <p style="color: #9ca3af; font-size: 0.95rem;">Ask questions about your documents or search the web</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Actions section with enhanced styling
        st.markdown("""
        <div style="background: white; padding: 1.5rem; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); margin-bottom: 1.5rem;">
            <h2 style="margin: 0; padding-bottom: 0.5rem; border-bottom: 2px solid #e5e7eb; font-size: 1.25rem;">🔍 Actions</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Display document summary if it exists in session state
        if 'doc_summary' in st.session_state and st.session_state['doc_summary']:
            st.markdown("""
            <div style="background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;">
            """, unsafe_allow_html=True)
            with st.expander("📄 Document Summary", expanded=True):
                st.markdown(f"<div class='summary-box'>{st.session_state['doc_summary']}</div>", unsafe_allow_html=True)
                
                # Add a button to generate audio for document summary
                if st.button("🔊 Generate Audio", key="generate_doc_audio_btn", 
                           disabled=st.session_state.is_processing, use_container_width=True):
                    st.session_state.is_processing = True
                    st.session_state.current_operation = "Generating Doc Audio"
                    st.session_state['active_summary_type'] = 'doc'
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display link summary if it exists in session state
        if 'link_summary' in st.session_state and st.session_state['link_summary']:
            st.markdown("""
            <div style="background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;">
            """, unsafe_allow_html=True)
            with st.expander("🌐 Link Summary", expanded=True):
                st.markdown(f"<div class='summary-box'>{st.session_state['link_summary']}</div>", unsafe_allow_html=True)
                
                # Add a button to generate audio for link summary
                if st.button("🔊 Generate Audio", key="generate_link_audio_btn", 
                           disabled=st.session_state.is_processing, use_container_width=True):
                    st.session_state.is_processing = True
                    st.session_state.current_operation = "Generating Link Audio"
                    st.session_state['active_summary_type'] = 'link'
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display audio player for document summary
        if (st.session_state.get('doc_audio_available', False) and 
            'doc_audio_base64' in st.session_state and 
            st.session_state.get('last_doc_summary') == st.session_state['doc_summary']):
            st.markdown("""
            <div style="background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;">
            """, unsafe_allow_html=True)
            with st.expander("🔊 Document Audio Player", expanded=True):
                try:
                    audio_base64 = st.session_state['doc_audio_base64']
                    audio_html = f"""
                    <div style="margin: 15px 0; padding: 15px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); border-radius: 12px;">
                        <audio controls class="audio-player" style="width: 100%;">
                            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="⬇️ Download Audio",
                        data=base64.b64decode(audio_base64),
                        file_name="document_summary.mp3",
                        mime="audio/mp3",
                        key="doc_summary_audio_download",
                        use_container_width=True
                    )
                except Exception as e:
                    st.warning("Could not load audio player. Please try generating the audio again.")
                    st.session_state['doc_audio_available'] = False
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Display audio player for link summary
        if (st.session_state.get('link_audio_available', False) and 
            'link_audio_base64' in st.session_state and 
            st.session_state.get('last_link_summary') == st.session_state['link_summary']):
            st.markdown("""
            <div style="background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); margin-bottom: 1rem;">
            """, unsafe_allow_html=True)
            with st.expander("🔊 Link Audio Player", expanded=True):
                try:
                    audio_base64 = st.session_state['link_audio_base64']
                    audio_html = f"""
                    <div style="margin: 15px 0; padding: 15px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); border-radius: 12px;">
                        <audio controls class="audio-player" style="width: 100%;">
                            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
                    
                    st.download_button(
                        label="⬇️ Download Audio",
                        data=base64.b64decode(audio_base64),
                        file_name="link_summary.mp3",
                        mime="audio/mp3",
                        key="link_summary_audio_download",
                        use_container_width=True
                    )
                except Exception as e:
                    st.warning("Could not load audio player. Please try generating the audio again.")
                    st.session_state['link_audio_available'] = False
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Execute audio generation for document summary
        if st.session_state.is_processing and st.session_state.current_operation == "Generating Doc Audio":
            show_spinner_overlay("Generating Audio", "Converting document summary to speech")
            
            audio_data = text_to_speech(st.session_state['doc_summary'])
            
            st.session_state.is_processing = False
            st.session_state.current_operation = None
            
            if audio_data:
                st.session_state['doc_audio_base64'] = audio_data
                st.session_state['doc_audio_available'] = True
                st.session_state['last_doc_summary'] = st.session_state['doc_summary']
                st.success("Audio generated successfully!")
            else:
                st.error("Failed to generate audio. Please try again.")
            
            st.rerun()
        
        # Execute audio generation for link summary
        if st.session_state.is_processing and st.session_state.current_operation == "Generating Link Audio":
            show_spinner_overlay("Generating Audio", "Converting link summary to speech")
            
            audio_data = text_to_speech(st.session_state['link_summary'])
            
            st.session_state.is_processing = False
            st.session_state.current_operation = None
            
            if audio_data:
                st.session_state['link_audio_base64'] = audio_data
                st.session_state['link_audio_available'] = True
                st.session_state['last_link_summary'] = st.session_state['link_summary']
                st.success("Audio generated successfully!")
            else:
                st.error("Failed to generate audio. Please try again.")
            
            st.rerun()
        
        # Summarize section with enhanced styling
        st.markdown("""
        <div style="background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); margin-top: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 1rem; margin-top: 0;">📊 Summarization Tools</h3>
        """, unsafe_allow_html=True)
        
        # Summarize Documents button
        if st.button("📝 Summarize Documents", use_container_width=True, 
                    disabled=st.session_state.is_processing or not uploaded_files):
            st.session_state.is_processing = True
            st.session_state.current_operation = "Summarizing Documents"
            st.rerun()
        
        st.markdown("<div style='margin: 0.75rem 0;'></div>", unsafe_allow_html=True)
        
        # Summarize Links button
        if st.button("🌐 Summarize Links", use_container_width=True, 
                    disabled=st.session_state.is_processing or not st.session_state.websites):
            st.session_state.is_processing = True
            st.session_state.current_operation = "Summarizing Links"
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Execute document summarization if flagged
        if st.session_state.is_processing and st.session_state.current_operation == "Summarizing Documents":
            show_spinner_overlay("Summarizing Documents", "Analyzing document content and generating summary")
            
            doc_list = []
            
            # Process uploaded files only
            if uploaded_files:
                for file in uploaded_files:
                    docs = extract_text_from_file(file)
                    if docs:
                        doc_list.extend(docs)
            
            if doc_list:
                try:
                    # Use the summarize_documents function
                    summary = summarize_documents(doc_list)
                    st.session_state['doc_summary'] = summary
                    
                    # Clear any existing audio when generating a new summary
                    st.session_state['doc_audio_available'] = False
                    st.session_state['last_doc_summary'] = summary
                    
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    st.success("Document summary generated successfully!")
                except Exception as e:
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    st.error(f"Error generating document summary: {str(e)}")
                    st.session_state['doc_summary'] = ""
            else:
                st.session_state.is_processing = False
                st.session_state.current_operation = None
                st.warning("Please upload documents first.")
            
            st.rerun()
        
        # Execute link summarization if flagged
        if st.session_state.is_processing and st.session_state.current_operation == "Summarizing Links":
            show_spinner_overlay("Summarizing Links", "Analyzing link content and generating summary")
            
            link_docs = []
            
            # Process websites only
            if st.session_state.websites:
                for url in st.session_state.websites:
                    docs = extract_text_from_url(url)
                    if docs:
                        link_docs.extend(docs)
            
            if link_docs:
                try:
                    # Use the summarize_documents function
                    summary = summarize_documents(link_docs)
                    st.session_state['link_summary'] = summary
                    
                    # Clear any existing audio when generating a new summary
                    st.session_state['link_audio_available'] = False
                    st.session_state['last_link_summary'] = summary
                    
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    st.success("Link summary generated successfully!")
                except Exception as e:
                    st.session_state.is_processing = False
                    st.session_state.current_operation = None
                    st.error(f"Error generating link summary: {str(e)}")
                    st.session_state['link_summary'] = ""
            else:
                st.session_state.is_processing = False
                st.session_state.current_operation = None
                st.warning("Please add website URLs first.")
            
            st.rerun()

if __name__ == "__main__":
    main()
