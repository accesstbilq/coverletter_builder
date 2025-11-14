import os
import csv
from functools import lru_cache
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from django.conf import settings

# Path to your CSV file
CSV_FILE_PATH = settings.BASE_DIR / "active_projects_2025-11-12_15-24-13.csv"

@lru_cache(maxsize=1)
def get_project_retriever():
    """
    Creates and caches a FAISS vector store retriever from the project CSV.
    Returns top 10 candidates for filtering by priority later.
    """
    print("--- Initializing RAG Pipeline (Loading Projects CSV)... ---")

    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        # return a safe retriever so callers don't break
        return FAISS.from_texts(["No projects found"], OpenAIEmbeddings()).as_retriever()

    try:
        docs: List[Document] = []        # hold Document objects only
        rows: List[dict] = []           # keep raw rows if you need them later

        with open(CSV_FILE_PATH, 'r', encoding='utf-8-sig') as f:
            # utf-8-sig will remove BOM if present in header
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            print("No projects loaded from CSV.")
            return FAISS.from_texts(["No projects found"], OpenAIEmbeddings()).as_retriever()

        for idx, row in enumerate(rows):
            # Normalize keys in case of BOM or inconsistent header names
            # Try common header names for project URL
            project_url = row.get('Project_URL') or row.get('ProjectUrl') or row.get('URL') or row.get('project_url') or row.get('\ufeffProject_URL') or "Unknown URL"

            # Priority parsing with fallback
            priority_raw = row.get('Priority', "") or ""
            try:
                priority = int(priority_raw)
            except (ValueError, TypeError):
                priority = 0

            # Build a richer page_content so embeddings capture more useful text
            categories = row.get('Categories', 'N/A')
            technology = row.get('Technology', 'N/A')
            title = row.get('Title') or row.get('ProjectName') or row.get('Name') or ""
            description = row.get('Description') or row.get('Notes') or ""

            page_content = " | ".join(
                x for x in [title.strip(), description.strip(), f"Categories: {categories}", f"Technology: {technology}"] if x
            )

            metadata = {
                'Project_URL': project_url,
                'Categories': categories,
                'Technology': technology,
                'Priority': priority,
                'source': str(CSV_FILE_PATH),
                'row_index': idx
            }

            doc = Document(page_content=page_content, metadata=metadata)
            docs.append(doc)

        # Create embeddings and the FAISS vector store
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(docs, embeddings)

        print(f"--- RAG Pipeline Initialized Successfully with {len(docs)} projects. ---")
        # Return retriever that fetches top 10 candidates
        return vectorstore.as_retriever(search_kwargs={"k": 10})

    except Exception as e:
        print(f"Error initializing RAG pipeline: {e}")
        return FAISS.from_texts(["Error loading projects"], OpenAIEmbeddings()).as_retriever()

def load_all_projects_from_csv():
    """
    Load all projects from CSV and return as list of dictionaries.
    Useful for filtering and scoring operations.
    """
    projects = []
    
    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        return projects
    
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert priority to int
                try:
                    priority = int(row.get('Priority', 0))
                except:
                    priority = 0
                
                projects.append({
                    'url': row.get('Project URL', ''),
                    'categories': row.get('Categories', ''),
                    'technology': row.get('Technology', ''),
                    'priority': priority
                })
        
        print(f"[DEBUG] Loaded {len(projects)} total projects from CSV")
        return projects
    
    except Exception as e:
        print(f"Error loading projects from CSV: {e}")
        return projects