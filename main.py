from openai import OpenAI
import json
import os
import sys
from dotenv import load_dotenv
from typing import List, Callable, Tuple, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

load_dotenv()

def main():
    
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    )

    def getUserMessage() -> Tuple[str, bool]:
        try:
            line = sys.stdin.readline()
            if not line:
                return "", False
            return line.strip("\n"), True
        except EOFError:
            return "", False

    tools = AvailableTools
    agent = Agent(client=client, getUserMessage=getUserMessage, tools=tools, tool_choice='auto')
    try:
        agent.Run()
    except Exception as e:
        print(f"Error: {str(e)}")

class Agent:
    def __init__(
        self,
        client: OpenAI,
        getUserMessage: Callable[[], Tuple[str, bool]],
        tools: List,
        tool_choice: str
    ):
        self.client = client
        self.getUserMessage = getUserMessage
        self.tools = tools
        self.tool_choice = tool_choice

    def Run(self):
        conversation = []
        
        ToolFunctions = {
            "ReadFiles": ReadFiles,
            "ListFiles": ListFiles
        }

        print("Chat with Claude (use 'ctrl-c' to quit)")

        read_user_input = True
        while True:
            if read_user_input:
                print("You: ", end="", flush=True)
                user_input, ok = self.getUserMessage()
                if not ok:
                    break

                user_message = {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_input
                        }
                    ]
                }
                conversation.append(user_message)

            message = self.runInference(conversation)
            conversation.append(message)
            
            tools_used = []
            for point in message.choices:
                if not point.message.tool_calls:
                    print(f"Claude: {point.message.content}")
                else:
                    print(f"Claude: {point.message.content}")
                    
                    for tool in point.message.tool_calls:
    
                        function_name = tool.function.name
                        function_to_call = ToolFunctions[function_name]
                        function_args = json.loads(tool.function.arguments)
                        function_response = function_to_call(**function_args)
                        
                        conversation.append(
                            {
                                'role': 'assistant',
                                'content': json.dumps(function_response)    
                            }
                        )
                        tools_used.append(function_name)
                    print(f"Tool: {tools_used}")
                    print(f'Claude: {function_response}')
            
            if len(tools_used) == 0:
                read_user_input = True
                continue
            
            read_user_input = False



    def runInference(self, conversation: List[dict]):

        message = self.client.chat.completions.create(
            model="anthropic/claude-3.5-haiku",
            max_tokens=1024,
            messages=conversation,
            tools=AvailableTools,
            tool_choice='auto'
        )

        return message


def ReadFiles(directory_path: str) -> str:
    try:
        files_and_dirs = os.listdir(directory_path)
        return json.dumps({"contents": files_and_dirs, "path": directory_path})
    except FileNotFoundError:
        return json.dumps({"error": f"Directory not found: {directory_path}"})
    except PermissionError:
        return json.dumps({"error": f"Permission denied for directory: {directory_path}"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred: {str(e)}"})



def ListFiles(directory_path: str = ".") -> str:
    try:
        entries = os.listdir(directory_path)
        return json.dumps({"files": entries})
    except FileNotFoundError:
        return json.dumps({"error": f"Directory not found: {directory_path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


AvailableTools = [
    {
        "type": "function",
        "function": {
            "name": "ReadFiles",
            "description": "Reads the names of all files and subdirectories in a given directory path and returns a JSON list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The path to the directory (e.g., 'C:/Users/username/Documents' or './data')."
                    }
                },
                "required": ["directory_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ListFiles",
            "description": "Lists the names of all entries (files and directories) in a given directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "The path to the directory, e.g., 'data/documents'. Defaults to the current directory (.)."
                    }
                },
                "required": ["directory_path"],
            }
        }
    }
]

if __name__ == "__main__":
    main()
