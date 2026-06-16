from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.config import settings

def get_model():
    model = ChatGoogleGenerativeAI(
        model="gemma-4-26b-a4b-it",
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
        streaming=True
    )
    return model

def get_embedding_model():
    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2", 
        google_api_key=settings.GOOGLE_API_KEY
    )
    return embedding_model
