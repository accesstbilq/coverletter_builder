from ..rag_vectors import get_project_retriever
from langchain_core.tools import tool

@tool
def find_relevant_past_projects(query: str) -> str:
    """
    Search the stored project vectors for projects relevant to the query.
    Returns a concise formatted string of the top 3 most relevant matches
    (URL + short summary) for the agent to use.
    """
    print(f"--- RAG Tool Called with Query: {query} ---")
    
    try:
        retriever = get_project_retriever()
        # Retriever already handles similarity search.
        retrieved_docs = retriever.invoke(query)
    except Exception as e:
        return f"Error while retrieving projects: {e}"

    if not retrieved_docs:
        return "No relevant past projects found in the database."

    # Only keep the top 3 results to avoid noise
    top_docs = retrieved_docs[:3]

    formatted_results = []
    for i, doc in enumerate(top_docs, start=1):
        content = (doc.page_content or "").strip()

        # Try to extract URL from the content if you embed it like "URL: https://..."
        url = None
        for segment in content.split(" | "):
            seg = segment.strip()
            if seg.lower().startswith("url:"):
                url = seg[4:].strip()
                break

        # Shorten very long text – we just want a compact summary for the agent
        max_len = 600
        if len(content) > max_len:
            content = content[:max_len].rsplit(" ", 1)[0] + "..."

        parts = [f"Result {i}:"]
        if url:
            parts.append(f"- URL: {url}")
        parts.append(f"- Summary: {content}")

        formatted_results.append("\n".join(parts))

    print(f"--- RAG Tool Returned {len(top_docs)} Relevant Projects ---")
    print(top_docs)
    return "\n\n---\n\n".join(formatted_results)
