# forecaster_llm.py

from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import json
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Initialize LLM
llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_CHAT_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0  # Zero temp for more consistent answers
)

# Embedding model for vector store
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

# Prompt Template for retrieval-augmented generation (RAG)
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
Use the following historical context to help answer the user's question.

Context:
{context}

Question:
{question}

Answer (format your answer as JSON):
""".strip()
)

# ========== WHAT-IF ANALYSIS FOR ONE DAY ==========
def query_llm_what_if_one_day(input_data: dict, client_name: str, debug=False):
    vector_store = load_local_vectorstore()

    question = (
        f"Client: {client_name}\n"
        f"Given Volatility={input_data['Volatility']}, Interest Rate={input_data['Interest Rate']}, should a margin call be issued today?\n"
        f"Margin Call Amount = MTM - Collateral - Threshold (Only if > MTA).\n"
        f"Provide explanation.\n\n"
        f"Respond in JSON format with these keys:\n"
        f"- 'Client'\n"
        f"- 'Date'\n"
        f"- 'MarginCallRequired'\n"
        f"- 'MarginCallAmount'\n"
        f"- 'ConfidenceScore' (between 0% and 100%)\n"
        f"- 'Comments' (brief explanation)"
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 10})

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

    response = qa_chain.run(question)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON returned by LLM", "raw_output": response}


# ========== FORECASTING FOR NEXT 3 DAYS ==========
def query_llm_forecast_from_history(client_name: str, debug=False):
    vector_store = load_local_vectorstore()

    today = datetime.today()
    t_plus_1 = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    t_plus_2 = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    t_plus_3 = (today + timedelta(days=3)).strftime('%Y-%m-%d')

    question = f"""
Client: {client_name}
Today's Date: {today.strftime('%Y-%m-%d')}

Based on historical data, forecast margin calls for the next 3 days:
- {t_plus_1}
- {t_plus_2}
- {t_plus_3}

Instructions:
1. For each date, determine if a margin call will be needed.
2. Use: Margin Call Amount = MTM - Collateral - Threshold
3. Only issue a margin call if the result > MTA.
4. Estimate your confidence score (0%-100%) for each prediction.
5. Provide an explanation.

Respond in JSON array format like:
[
  {{
    "Client": "{client_name}",
    "Date": "{t_plus_1}",
    "MarginCallRequired": "Yes/No",
    "MarginCallAmount": "$...",
    "ConfidenceScore": "90%",
    "Comments": "Brief explanation without using T+1 terminology."
  }},
  {{
    "Client": "{client_name}",
    "Date": "{t_plus_2}",
    ...
  }},
  {{
    "Client": "{client_name}",
    "Date": "{t_plus_3}",
    ...
  }}
]
""".strip()

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

    response = qa_chain.run(question)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON returned by LLM", "raw_output": response}


# ========== ASK ANYTHING ==========
def query_llm_ask_anything(query: str, debug=False):
    vector_store = load_local_vectorstore()

    retriever = vector_store.as_retriever(search_kwargs={"k": 20})

    if debug:
        docs = retriever.get_relevant_documents(query)
        print("\n=== Retrieved Documents ===")
        for i, doc in enumerate(docs):
            print(f"\nDoc {i+1}:\n{doc.page_content}")

    plain_text_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
Use the following historical context to answer the user's question in plain language.

Context:
{context}

Question:
{question}

Answer:
""".strip()
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        chain_type_kwargs={"prompt": plain_text_prompt}
    )

    return qa_chain.run(query)