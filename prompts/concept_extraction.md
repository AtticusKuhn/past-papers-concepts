# HCI Concept Extraction Task

## Context
You are analyzing text from a Cambridge Computer Science Tripos exam paper focusing on Human-Computer Interaction (HCI). Your task is to identify key HCI concepts, techniques, evaluation methods, and user interface principles present in the text.

## Instructions
1. Extract all significant HCI concepts, user interface techniques, evaluation methodologies, design principles, and related terms mentioned in the text.
2. For each concept, identify:
   - The concept name (clear and standardized)
   - A brief description (if context is available)
   - The category/field it belongs to (e.g., Interaction Design, User Research, Evaluation Methods, Cognitive Models, Interface Technologies, etc.)
   - Any parent concepts it relates to
   - Related concepts mentioned in the same context

3. Rate your confidence in each concept extraction (0.0-1.0)
4. Include the surrounding context where the concept appears

## Response Format
Provide your analysis in JSON format:
```json
{{
  "concepts": [
    {{
      "name": "Concept name",
      "description": "Brief description based on context",
      "category": "Field of computer science",
      "parent_concept": "Broader concept (if applicable)",
      "related_concepts": ["Related concept 1", "Related concept 2"],
      "confidence": 0.95,
      "context": "The surrounding text where the concept appears"
    }}
  ]
}}
```

## Input Text
{text}
