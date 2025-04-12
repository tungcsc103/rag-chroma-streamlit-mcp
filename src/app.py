import streamlit as st
import requests
from pathlib import Path
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Local RAG System",
    page_icon="🔍",
    layout="wide"
)

# Constants
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8001")
API_URL = f"http://{API_HOST}:{API_PORT}"

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
    default_formats = ["pdf", "doc", "docx", "txt", "md", "csv"]
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
                            
                            # Show document metadata in an expander
                            with st.expander(f"Document Details - {file.name}"):
                                st.json(result["metadata"])
                        else:
                            st.error(f"Failed to upload {file.name}: {response.text}")
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
    
    # Query input
    query = st.text_input("Enter your question:")
    top_k = st.slider("Number of results to return", min_value=1, max_value=10, value=3)
    
    if st.button("Search"):
        if query:
            with st.spinner('Searching...'):
                try:
                    response = requests.post(
                        f"{API_URL}/query",
                        json={"query": query, "top_k": top_k}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()
                        
                        # Display results in expandable containers
                        for i, (doc, meta, dist) in enumerate(zip(
                            results["documents"],
                            results["metadata"],
                            results["distances"]
                        )):
                            similarity_score = 1 - dist
                            score_color = "green" if similarity_score > 0.8 else "orange" if similarity_score > 0.5 else "red"
                            
                            with st.expander(
                                f"Result {i+1} - {meta.get('filename', 'Unknown')} "
                                f"(Similarity: :{score_color}[{similarity_score:.2f}])"
                            ):
                                st.markdown("**Document Content:**")
                                st.write(doc)
                                st.markdown("**Document Metadata:**")
                                st.json(meta)
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Error querying the system: {str(e)}")
        else:
            st.warning("Please enter a question.")

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
                        st.metric("Total Documents", stats["count"])
                        st.metric("Collection Name", stats["name"])
                    
                    with col2:
                        st.subheader("Collection Metadata")
                        st.json(stats["metadata"])
                else:
                    st.error(f"Error fetching stats: {response.text}")
            except Exception as e:
                st.error(f"Error connecting to the API: {str(e)}")

if __name__ == "__main__":
    main() 