#rag_index.py
import os
import pandas as pd
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import AzureOpenAIEmbeddings

# Load environment variables
load_dotenv()

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    print(f"📊 Loaded {len(df)} rows from {csv_path}")
    return df

def prepare_documents(df):
    docs = []
    for _, row in df.iterrows():
        text = "\n".join([f"{col}: {val}" for col, val in row.items()])
        docs.append(Document(page_content=text))
    print(f"📄 Split into {len(docs)} chunks for embedding")
    return docs

def build_vectorstore():
    df = load_data("MarginCallData.csv")
    docs = prepare_documents(df)

    embedding_model = AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
        deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
    )

    vectorstore = FAISS.from_documents(docs, embedding_model)
    vectorstore.save_local("faiss_index")
    print("✅ FAISS index saved to 'faiss_index' folder.")

if __name__ == "__main__":
    print(f"📁 Current working directory: {os.getcwd()}")
    build_vectorstore()