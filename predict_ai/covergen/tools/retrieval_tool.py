# predict_ai/covergen/tools/retrieval_tool.py

from langchain_core.tools import tool
from ..rag_setup import get_project_retriever
from langchain_core.documents import Document

@tool
def find_relevant_past_projects(query: str) -> str:
    """
    Searches the company's past project database (a CSV) to find projects
    relevant to the user's query (e.g., "Shopify plugin for subscriptions").
    Returns a formatted string of the top 3 matches.
    """
    print(f"--- RAG Tool Called with Query: {query} ---")
    retriever = get_project_retriever()
    
    try:
        retrieved_docs = retriever.invoke(query)
    except Exception as e:
        return f"Error while retrieving projects: {e}"

    if not retrieved_docs:
        return "No relevant past projects found in the database."

    # Format the results into a clean string for the LLM
    formatted_results = []
    for i, doc in enumerate(retrieved_docs):
        url = doc.metadata.get('Project_URL', 'N/A')
        categories = doc.metadata.get('Categories', 'N/A')
        tech = doc.metadata.get('Technology', 'N/A')
        
        formatted_results.append(
            f"Result {i+1}:\n"
            f"- Project URL: {url}\n"
            f"- Categories: {categories}\n"
            f"- Technology: {tech}\n"
        )

    print(f"--- RAG Tool Found {len(retrieved_docs)} Projects ---")
    return "\n---\n".join(formatted_results)