import json
import os
import pydantic
import time
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from schema import AgentOutputSchema
from tools import get_repo_tree, read_code_file, update_portfolio_db

# Initialize Gemini Client
try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    client = None
    print(f"Warning: Could not initialize Gemini Client: {e}")

PERSONA = """
Name: AntiGravity Core
Role: Autonomous Technical Portfolio Architect and Code Analyst
Context: Operating as a background agent integrated with the GitHub API and a native web portfolio database.

Objective:
Your primary goal is to autonomously analyze raw repository code, extract technical complexities, and synthesize zero-hallucination project summaries optimized for developer portfolios.

Strict Output Rules:
- NEVER hallucinate features, dependencies, or architectural choices not explicitly present in the source files.
- Maintain high precision: if a project uses native browser APIs rather than external heavy wrappers, highlight that exact technical distinction.
- When ready to update the site, you must output a single, valid JSON object matching the AgentOutputSchema to complete the task. Do not prepend markdown formatting like ```json.
- If metrics like 'latency_target' and 'operational_efficiency' are not explicitly defined in the code, simply omit them or set them to null.
"""

def analyze_repository(repo_path: str, project_id: str):
    if not client:
        print("Gemini client not initialized. Please set GEMINI_API_KEY environment variable.")
        return

    # Wrapper functions for the agent tools
    def agent_get_repo_tree():
        """Returns the file directory structure of the repository."""
        return get_repo_tree(repo_path)
    
    def agent_read_code_file(file_path: str):
        """Fetches raw text contents of a specific file."""
        return read_code_file(repo_path, file_path)

    # Use gemini-2.0-flash as requested to prevent 404 errors
    chat = client.chats.create(
      model = 'gemini-1.5-flash',
        config=types.GenerateContentConfig(
            system_instruction=PERSONA,
            tools=[agent_get_repo_tree, agent_read_code_file],
            temperature=0.2
        )
    )

    def send_message_with_retry(message):
        """Helper to catch Rate Limits and Server Errors and retry with exponential backoff."""
        max_retries = 6
        base_wait = 5
        
        for attempt in range(max_retries):
            try:
                return chat.send_message(message)
            except Exception as e:
                print(f"🚨 Google API Error: {e}")
                error_str = str(e)
                if "429" in error_str or "503" in error_str or "RESOURCE_EXHAUSTED" in error_str or "UNAVAILABLE" in error_str:
                    wait_time = base_wait * (2 ** attempt)  # 5, 10, 20, 40, 80, 160...
                    print(f"[API Overloaded] Attempt {attempt + 1}/{max_retries}. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    raise e
        raise Exception("Max retries exceeded for API requests due to persistent rate limiting or server overload.")

    print(f"Starting analysis of repository at {repo_path}...")
    prompt = f"Analyze the repository at {repo_path}. First explore the directory structure, then read the core logic files. Once you extract the technical complexities, you MUST output a JSON response matching the AgentOutputSchema."

    response = send_message_with_retry(prompt)

    # Graceful Tool Failures: Execution Loop
    max_iterations = 10
    for i in range(max_iterations):
        if response.function_calls:
            results = []
            for function_call in response.function_calls:
                name = function_call.name
                args = function_call.args
                print(f"Agent called tool: {name}({args})")
                
                try:
                    if name == "agent_get_repo_tree":
                        res = agent_get_repo_tree()
                    elif name == "agent_read_code_file":
                        if 'file_path' in args:
                            res = agent_read_code_file(args['file_path'])
                        else:
                            res = "Error: Missing required argument 'file_path'."
                    else:
                        res = f"Error: Unknown tool {name}"
                except Exception as e:
                    res = f"Tool Error: {str(e)}"
                
                results.append(types.Part.from_function_response(
                    name=name,
                    response={"result": res}
                ))
            
            # Send tool results back to the agent
            response = send_message_with_retry(results)
            continue
            
        # If no tool calls, validate the JSON output
        try:
            raw_text = response.text.strip()
            # Clean potential markdown output
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            
            raw_text = raw_text.strip()
            
            # Validate JSON syntax
            parsed_json = json.loads(raw_text)
            
            # Validate against Pydantic schema
            validated_data = AgentOutputSchema(**parsed_json)
            
            # If valid, execute the database update tool (Data Integrity Guardrail)
            print("\\nValid JSON payload received. Updating portfolio database...")
            result = update_portfolio_db(project_id, validated_data.model_dump())
            print(result)
            return validated_data
            
        except json.JSONDecodeError:
            error_msg = "Error: Invalid JSON format received. Re-parse your output and strictly match the JSON Schema. Do not include markdown code blocks or conversational text."
            print(f"[Graceful Failure Triggered] Invalid JSON format. Requesting correction...")
            response = send_message_with_retry(error_msg)
        except pydantic.ValidationError as e:
            error_msg = f"Error validating JSON Schema: {str(e)}. Re-parse your output and strictly match the JSON Schema."
            print(f"[Graceful Failure Triggered] Schema mismatch. Requesting correction...")
            response = send_message_with_retry(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}."
            print(f"[Graceful Failure Triggered] {error_msg}")
            response = send_message_with_retry(error_msg)
            
    print("Max iterations reached. Analysis failed.")
