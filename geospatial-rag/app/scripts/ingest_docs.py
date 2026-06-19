import os
import argparse
import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
import sys

# Add the parent directory to sys.path so we can import app modules when running as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ai.llm import get_embedding_model
from app.config import settings

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "../../../data/chroma_db")

def ingest_pdf(pdf_path: str):
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found at: {pdf_path}")
        return

    logger.info(f"Loading PDF: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    logger.info(f"Loaded {len(documents)} pages.")

    logger.info("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} text chunks.")

    logger.info("Initializing embedding model...")
    embedding_model = get_embedding_model()

    logger.info(f"Ingesting into ChromaDB at {CHROMA_PERSIST_DIR}...")
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    
    # Initialize the vector store empty
    vector_store = Chroma(
        embedding_function=embedding_model,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name="documentation"
    )
    
    import time
    BATCH_SIZE = 80 # Keep under the 100 requests/min free tier limit
    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        logger.info(f"Ingesting batch {i//BATCH_SIZE + 1} of {(len(chunks)-1)//BATCH_SIZE + 1}...")
        vector_store.add_documents(batch)
        
        if i + BATCH_SIZE < len(chunks):
            logger.info("Sleeping for 65 seconds to avoid Google Gemini free-tier rate limits...")
            time.sleep(65)
            
    logger.info("Ingestion complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDF documentation into ChromaDB")
    parser.add_argument("--pdf", type=str, default="/home/ghassen/Bureau/geospatial-rag-app/geotrellis-readthedocs-io-en-v3.5.1.pdf", help="Path to the PDF file")
    args = parser.parse_args()
    
    ingest_pdf(args.pdf)
