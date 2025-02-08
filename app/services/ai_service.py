import openai
import json
import os
from typing import Dict

# Set OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

def convert_text_to_json(text: str) -> Dict:
    """
    Convert text to structured JSON using OpenAI assistant
    """
    system_prompt = """
    ## Prompt: Transform News Items into Structured JSON

    ### **Role**
    You are an AI language model that can read and analyze various news items, then convert them into a specified JSON format.

    ### **Context**
    You receive multiple topics of news items, each corresponding to a predefined category. The topics include:
	•	asean_statements_and_communiques
	•	indonesia_and_asean_secretariat_news
	•	trafficking_in_persons_migrant_workers
	•	climate_change
	•	humanitarian_and_disaster_responses
	•	asean_dialogue_partners
	•	labour_migration
	•	economic_and_political_affairs
	•	lnob
	•	others

    Each topic has:
    - A title
    - One or more news items (each with its own title, link, **date (Month DD, YYYY)**, and summary)

    ### **Required JSON Structure**
    {
    "json_data": {
        "document": {
        "month": "October 2024",
        "sections": [
            {
            "title": "<topic_name_in_snake_case>",
            "bullets": [
                {
                "text": "<news_item_title>",
                "link": "<news_item_link>",
                "date": "<Month DD, YYYY>",
                "styles": ["bold", "underline"],
                "content": "<summary or additional details>"  // Optional: exclude for asean_statements_and_communiques
                }
            ]
            }
        ]
        }
    }
    }

    ### **Task**
    1. Produce valid JSON following the exact structure above
    2. The "month" field in "document" should be "October 2024" unless instructed otherwise
    3. Each "date" must be in Month DD, YYYY format
    4. For "asean_statements_and_communiques" topic, exclude the "content" field
    5. For other topics, include the "content" field with summary or relevant text
    6. All bullet items must have "styles": ["bold", "underline"]
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            response_format={"type": "json_object"} 
        )
        
        # Validate response structure
        if not response.choices or not hasattr(response.choices[0].message, "content"):
            raise ValueError("Invalid response format from OpenAI API")

        json_str = response.choices[0].message.content

        # Convert response to JSON
        parsed_json = json.loads(json_str)

        # Validate required keys
        if not isinstance(parsed_json, dict):
            raise ValueError("Response is not a valid JSON object")
        
        if "json_data" not in parsed_json:
            raise ValueError("Response missing 'json_data' key")
            
        if "document" not in parsed_json["json_data"]:
            raise ValueError("Response missing 'document' key")

        return parsed_json

    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON response: {str(e)}")
    except Exception as e:
        raise Exception(f"Error converting text to JSON: {str(e)}")
