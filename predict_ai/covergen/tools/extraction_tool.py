from langchain_core.tools import tool
from typing import Dict, List, Literal
from pydantic import BaseModel, Field


class CoverLetterExtraction(BaseModel):
    """Structured extraction from cover letter"""
    greeting: str = Field(description="Greeting with client name if available")
    client_name: str = Field(description="Client's name or empty string")
    main_objective: str = Field(description="Primary goal in one sentence (max 50 words)")
    project_scope: str = Field(description="2-3 sentence description of the project")
    reference_sites: List[str] = Field(description="URLs or website names mentioned", default_factory=list)
    technologies_needed: Dict[str, List[str]] = Field(
        description="Technologies required grouped by category",
        default_factory=dict
    )
    tool_recommendations: Dict[str, List[str]] = Field(
        description="Specific plugins/apps/services with reasoning",
        default_factory=dict
    )
    project_category: Literal["new_website", "existing_website", "website_update", "unclear"] = Field(
        description="Type of project"
    )
    non_tech_requirements: List[str] = Field(
        description="Timeline, budget, deliverables, etc.",
        default_factory=list
    )
    clarifying_questions: List[str] = Field(
        description="3-5 specific questions to understand project better",
        default_factory=list
    )
    suggested_response: str = Field(
        description="Professional 2-3 paragraph cover letter response"
    )


def get_extraction_tool():
    """Returns the structured extraction tool"""
    
    @tool("extract_cover_letter_info", args_schema=CoverLetterExtraction)
    def extract_cover_letter_info(
        greeting: str,
        client_name: str,
        main_objective: str,
        project_scope: str,
        reference_sites: List[str],
        technologies_needed: Dict[str, List[str]],
        tool_recommendations: Dict[str, List[str]],
        project_category: Literal["new_website", "existing_website", "website_update", "unclear"],
        non_tech_requirements: List[str],
        clarifying_questions: List[str],
        suggested_response: str
    ) -> Dict:
        """
        Extract structured information from a cover letter.
        
        This tool analyzes a client's cover letter and extracts:
        - Client information (name, greeting)
        - Project details (objective, scope, category)
        - Technical requirements (technologies, tools)
        - Non-technical requirements (timeline, budget)
        - Clarifying questions
        - Suggested professional response
        """
        return {
            "greeting": greeting,
            "client_name": client_name,
            "main_objective": main_objective,
            "project_scope": project_scope,
            "reference_sites": reference_sites,
            "technologies_needed": technologies_needed,
            "tool_recommendations": tool_recommendations,
            "project_category": project_category,
            "non_tech_requirements": non_tech_requirements,
            "clarifying_questions": clarifying_questions,
            "suggested_response": suggested_response
        }
    
    return extract_cover_letter_info