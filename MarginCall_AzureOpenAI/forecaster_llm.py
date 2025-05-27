from dotenv import load_dotenv
import os
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

load_dotenv()

# Initialize LLM
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0
)

# Embedding model
embedding_model = AzureOpenAIEmbeddings(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION"),
    deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
)

# Load FAISS vectorstore
def load_local_vectorstore():
    return FAISS.load_local(
        "faiss_index",
        embedding_model,
        allow_dangerous_deserialization=True
    )

# Prompt Template
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
Use the following historical context to help answer the user's question.

Context:
{context}

Question:
{question}

Answer:
""".strip()
)

# ========== WHAT-IF ANALYSIS ==========
def query_llm_what_if_one_day(input_data: dict, debug=False):
    vector_store = load_local_vectorstore()

    # Construct a query that embeds user input as a semantic query
    question = (
        f"Given MTM={input_data['MTM']}, Collateral={input_data['Collateral']}, Threshold={input_data['Threshold']}, "
        f"Volatility={input_data['Volatility']}, FX Rate={input_data['FX Rate']}, Interest Rate={input_data['Interest Rate']}, "
        f"MTA={input_data['MTA']}, Currency={input_data['Currency']}, should a margin call be issued today?\n"
        f"Margin Call Amount = MTM - Collateral - Threshold (Only if > MTA). Provide explanation."
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 10})
    
    if debug:
        # Debug: print top matching documents
        docs = retriever.get_relevant_documents(question)
        print("\n=== Retrieved Documents ===")
        for i, doc in enumerate(docs):
            print(f"\nDoc {i+1}:\n{doc.page_content}")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={"prompt": prompt_template}
    )

    return qa_chain.run(question)

# ========== FORECASTING ==========
def query_llm_forecast_from_history(debug=False):
    vector_store = load_local_vectorstore()
    question = """
Based on historical data, forecast margin calls for the next 3 days (T+1 to T+3).

Instructions:
1. Estimate if a margin call will be needed on each day.
2. Use: Margin Call Amount = MTM - Collateral - Threshold
3. Only issue margin call if result > MTA.
4. Provide explanations for each day.

Output format:
Day: T+1  
Margin Call Required: Yes/No  
Margin Call Amount: $...  
Comments: ...

Day: T+2  
...

Day: T+3  
...
    """

    retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    if debug:
        docs = retriever.get_relevant_documents(question)
        print("\n=== Retrieved Documents ===")
        for i, doc in enumerate(docs):
            print(f"\nDoc {i+1}:\n{doc.page_content}")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={"prompt": prompt_template}
    )

    return qa_chain.run(question)

# ========== ASK ANYTHING ==========
def query_llm_ask_anything(query: str, debug=False):
    vector_store = load_local_vectorstore()

    retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    if debug:
        docs = retriever.get_relevant_documents(query)
        print("\n=== Retrieved Documents ===")
        for i, doc in enumerate(docs):
            print(f"\nDoc {i+1}:\n{doc.page_content}")

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={"prompt": prompt_template}
    )

    return qa_chain.run(query)