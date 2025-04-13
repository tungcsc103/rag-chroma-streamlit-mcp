import streamlit as st
import requests
from pathlib import Path
import json
import os
from dotenv import load_dotenv
import pyperclip

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Local RAG System",
    page_icon="🔍",
    layout="wide"
)

# Get API URL from environment variables
API_HOST = os.getenv('BACKEND_HOST', 'localhost')
API_PORT = os.getenv('BACKEND_PORT', '8001')
API_URL = f"http://{API_HOST}:{API_PORT}"

def copy_to_clipboard(text):
    """Helper function to copy text to clipboard and show a success message."""
    try:
        pyperclip.copy(text)
        st.toast("✅ Copied to clipboard!")
    except Exception as e:
        st.toast("❌ Failed to copy to clipboard")
        print(f"Error copying to clipboard: {str(e)}")

# Get supported file types from the API
def get_supported_formats():
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            formats = response.json().get("supported_formats", [])
            if formats:
                return formats
            st.warning("No supported formats returned by the API. Using default formats.")
        else:
            st.warning(f"Failed to get supported formats from API: {response.text}")
        
    except Exception as e:
        st.warning(f"Error connecting to API: {str(e)}")
    
    # Default formats if API call fails
    default_formats = ["pdf", "doc", "docx", "txt", "md", "csv", "epub"]
    return default_formats

def main():
    st.title("🔍 Local RAG System")
    st.sidebar.title("Navigation")
    
    # Navigation
    page = st.sidebar.radio("Choose a page", ["Upload Documents", "Query Documents", "System Stats"])
    
    if page == "Upload Documents":
        show_upload_page()
    elif page == "Query Documents":
        show_query_page()
    else:
        show_stats_page()

def show_upload_page():
    st.header("📄 Upload Documents")
    st.write("Upload documents to the RAG system.")
    
    try:
        # Get API information including supported formats
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            api_info = response.json()
            supported_formats = api_info.get("supported_formats", [])
            format_descriptions = api_info.get("format_descriptions", {})
            
            # Show supported formats with descriptions
            with st.expander("Supported File Formats"):
                st.write("The following file formats are supported:")
                for fmt in supported_formats:
                    description = format_descriptions.get(fmt, "Supported document format")
                    st.write(f"- **.{fmt}** - {description}")
        else:
            supported_formats = get_supported_formats()
            st.warning("Using default supported formats.")
            
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=supported_formats,
            accept_multiple_files=True
        )
        
        if uploaded_files:
            for file in uploaded_files:
                with st.spinner(f'Uploading {file.name}...'):
                    try:
                        files = {"file": (file.name, file, "application/octet-stream")}
                        response = requests.post(f"{API_URL}/upload", files=files)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success(f"Successfully uploaded {file.name}")
                            
                            # Show document details in an expander
                            with st.expander(f"Document Details - {file.name}"):
                                if "document_id" in result:
                                    st.write(f"Document ID: {result['document_id']}")
                                if "message" in result:
                                    st.write(f"Status: {result['message']}")
                        else:
                            error_detail = response.json().get('detail', 'Unknown error')
                            st.error(f"Failed to upload {file.name}: {error_detail}")
                    except Exception as e:
                        st.error(f"Error uploading {file.name}: {str(e)}")
                        
    except Exception as e:
        st.error(f"Error connecting to the API: {str(e)}")
        st.warning("Using default supported formats.")
        supported_formats = get_supported_formats()
        
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=supported_formats,
            accept_multiple_files=True
        )

def show_query_page():
    st.header("❓ Query Documents")
    st.write("Ask questions about your uploaded documents.")
    
    # Add custom CSS for better text display
    st.markdown("""
        <style>
        .chunk-text {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 10px;
            margin: 5px 0;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 200px;
            overflow-y: auto;
        }
        .expanded {
            max-height: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for search results and expander states if not exists
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'expander_states' not in st.session_state:
        st.session_state.expander_states = {}
    if 'expanded_chunks' not in st.session_state:
        st.session_state.expanded_chunks = set()
    
    def do_search():
        if st.session_state.query_input:  # Only search if query is not empty
            with st.spinner('Searching...'):
                try:
                    response = requests.post(
                        f"{API_URL}/query",
                        json={
                            "query": st.session_state.query_input,
                            "top_k": st.session_state.top_k,
                            "group_by_document": True
                        }
                    )
                    
                    if response.status_code == 200:
                        st.session_state.search_results = response.json()
                        # Initialize expander states for new results - all collapsed by default
                        st.session_state.expander_states = {
                            f"expander_{i}": False 
                            for i in range(len(response.json().get("results", [])))
                        }
                        # Reset expanded chunks on new search
                        st.session_state.expanded_chunks = set()
                except Exception as e:
                    st.error(f"Error querying the system: {str(e)}")
    
    # Query input
    query = st.text_input("Enter your question:", key="query_input", on_change=do_search)
    top_k = st.slider("Number of results to return", min_value=1, max_value=10, value=3, key="top_k")
    
    # Search button (keep this as an alternative to Enter)
    if st.button("Search"):
        do_search()
    
    # Display results if they exist
    if st.session_state.search_results:
        data = st.session_state.search_results
        
        if not data.get("results"):
            st.info("No results found for your query.")
            return
        
        # Display results in expandable containers
        for i, result in enumerate(data["results"]):
            # Calculate best similarity score
            best_similarity = 1 - result["best_distance"]
            score_color = "green" if best_similarity > 0.8 else "orange" if best_similarity > 0.5 else "red"
            
            # Get current expander state from session state
            expander_key = f"expander_{i}"
            current_state = st.session_state.expander_states.get(expander_key, False)
            
            # Create expander with current state
            with st.expander(
                f"Result {i+1} - {result['metadata'].get('filename', 'Unknown')} "
                f"(Similarity: :{score_color}[{best_similarity:.2f}])",
                expanded=current_state
            ) as exp:
                # Update expander state when clicked
                if exp:
                    st.session_state.expander_states[expander_key] = True
                else:
                    st.session_state.expander_states[expander_key] = False
                
                # Create two columns for content and metadata
                col1, col2 = st.columns([7, 3])
                
                with col1:
                    # Display each chunk with its similarity score and copy button
                    for j, chunk in enumerate(result["chunks"]):
                        chunk_similarity = 1 - chunk["distance"]
                        chunk_text = chunk["text"]
                        chunk_key = f"{i}-{j}"
                        
                        # Create a container for the chunk header
                        st.markdown(f"**Chunk {j+1} (Similarity: {chunk_similarity:.2f}):**")
                        
                        # Toggle button for expanding/collapsing text
                        is_expanded = chunk_key in st.session_state.expanded_chunks
                        if st.button(
                            "Show Less" if is_expanded else "Show More",
                            key=f"toggle_{chunk_key}"
                        ):
                            if is_expanded:
                                st.session_state.expanded_chunks.remove(chunk_key)
                            else:
                                st.session_state.expanded_chunks.add(chunk_key)
                            st.experimental_rerun()
                        
                        # Display the chunk text with custom styling
                        st.markdown(
                            f'<div class="chunk-text{" expanded" if is_expanded else ""}">{chunk_text}</div>',
                            unsafe_allow_html=True
                        )
                        
                        # Add copy button below the text
                        if st.button(f"📋 Copy Chunk {j+1}", key=f"copy_{chunk_key}"):
                            copy_to_clipboard(chunk_text)
                            # Preserve expander states after copying
                            st.session_state.expander_states[expander_key] = True
                
                with col2:
                    # Display document metadata
                    st.markdown("**Document Metadata:**")
                    st.json(result["metadata"])

def show_stats_page():
    st.header("📊 System Statistics")
    st.write("Current status of the RAG system.")
    
    if st.button("Refresh Stats"):
        with st.spinner('Fetching statistics...'):
            try:
                response = requests.get(f"{API_URL}/stats")
                
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Display stats in a nice format
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Chunks", stats["total_chunks"])
                        st.metric("Unique Documents", stats["unique_documents"])
                        st.metric("Collection Name", stats["name"])
                    
                    with col2:
                        st.subheader("Collection Metadata")
                        if stats.get("metadata"):
                            st.json(stats["metadata"])
                        else:
                            st.info("No collection metadata available")
                else:
                    st.error(f"Error fetching stats: {response.text}")
            except Exception as e:
                st.error(f"Error connecting to the API: {str(e)}")

if __name__ == "__main__":
    main() 