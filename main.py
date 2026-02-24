import json
import os
import sys
import os.path
from dotenv import load_dotenv
from typing import List, Callable, Tuple, Any, Optional
from dataclasses import dataclass, field
import anthropic
from pydantic import BaseModel, Field

load_dotenv()

def main():
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )

    def get_user_message() -> Tuple[str, bool]:
        try:
            line = sys.stdin.readline()
            if not line:
                return "", False
            return line.strip("\n"), True
        except EOFError:
            return "", False

    tools = [READ_FILE_DEFINITION, LIST_FILES_DEFINITION, EDIT_FILE_DEFINITION]
    agent = Agent(client=client, get_user_message=get_user_message, tools=tools)
    try:
        agent.Run()
    except Exception as e:
        print(f"Error: {str(e)}")

class Agent:
    def __init__(
        self,
        client: anthropic.Anthropic,
        get_user_message: Callable[[], Tuple[str, bool]],
        tools: List['ToolDefinition'], 
    ):
        self.client = client
        self.get_user_message = get_user_message
        self.tools = tools


    def Run(self):
        conversation = []

        print("Chat with Claude (use 'ctrl-c' to quit)")

        read_user_input = True
        while True:
            if read_user_input:
                print("You: ", end="", flush=True)
                user_input, ok = self.get_user_message()
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

            message = self.run_inference(conversation)
            
            message_param = {
                "role": "assistant",
                "content": []
            }
            for block in message.content:
                if block.type == "text":
                    message_param["content"].append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    message_param["content"].append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            conversation.append(message_param)

            tool_results = []
            for content in message.content:
                if content.type == "text":
                    print(f"Claude: {content.text}")
                elif content.type == "tool_use":
                    result = self.execute_tool(content.id, content.name, content.input)
                    tool_results.append(result)
            
            if len(tool_results) == 0:
                read_user_input = True
                continue
            
            read_user_input = False
            conversation.append({
                "role": "user",
                "content": tool_results
            })


    def execute_tool(self, id: str, name: str, input_data: Any) -> dict:
        tool_def = None
        found = False
        for tool in self.tools:
            if tool.name == name:
                tool_def = tool
                found = True
                break
        
        if not found:
            return {
                "type": "tool_result",
                "tool_use_id": id,
                "content": "tool not found",
                "is_error": True
            }

        print(f"tool: {name}({json.dumps(input_data)})")
        try:
            response, err = tool_def.function(input_data)
            if err is not None:
                return {
                    "type": "tool_result",
                    "tool_use_id": id,
                    "content": str(err),
                    "is_error": True
                }
            return {
                "type": "tool_result",
                "tool_use_id": id,
                "content": response,
                "is_error": False
            }
        except Exception as e:
            return {
                "type": "tool_result",
                "tool_use_id": id,
                "content": str(e),
                "is_error": True
            }


    def run_inference(self, conversation: List[dict]) -> anthropic.types.Message:
        anthropic_tools = []
        for tool in self.tools:
            anthropic_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })

        message = self.client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=conversation,
            tools=anthropic_tools,
        )
        return message

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    function: Callable[[Any], Tuple[str, Optional[Exception]]]

def GenerateSchema(model_class: type[BaseModel]) -> dict:
    schema = model_class.model_json_schema()
    
    res = {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }
    return res


class ReadFileInput(BaseModel):
    path: str = Field(..., description="The relative path of a file in the working directory.")

READ_FILE_INPUT_SCHEMA = GenerateSchema(ReadFileInput)

def ReadFile(input_data: Any) -> Tuple[str, Optional[Exception]]:
    try:
        read_file_input = ReadFileInput(**input_data)
        
        with open(read_file_input.path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, None
    except Exception as e:
        return "", e

READ_FILE_DEFINITION = ToolDefinition(
    name="read_file",
    description="Read the contents of a given relative file path. Use this when you want to see what's inside a file. Do not use this with directory names.",
    input_schema=READ_FILE_INPUT_SCHEMA,
    function=ReadFile,
)


class ListFilesInput(BaseModel):
    path: Optional[str] = Field(None, description="Optional relative path to list files from. Defaults to current directory if not provided.")

LIST_FILES_INPUT_SCHEMA = GenerateSchema(ListFilesInput)

def ListFiles(input_data: Any) -> Tuple[str, Optional[Exception]]:
    try:
        list_files_input = ListFilesInput(**input_data)
        
        directory = "."
        if list_files_input.path:
            directory = list_files_input.path

        files = []

        for root, dirs, filenames in os.walk(directory):
            for name in dirs:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, directory)
                if rel_path != ".":
                    files.append(rel_path + "/")
            for name in filenames:
                full_path = os.path.join(root, name)
                rel_path = os.path.relpath(full_path, directory)
                if rel_path != ".":
                    files.append(rel_path)
        
        return json.dumps(files), None
    except Exception as e:
        return "", e

LIST_FILES_DEFINITION = ToolDefinition(
    name="list_files",
    description="List files and directories at a given path. If no path is provided, lists files in the current directory.",
    input_schema=LIST_FILES_INPUT_SCHEMA,
    function=ListFiles,
)


class EditFileInput(BaseModel):
    path: str = Field(..., description="The path to the file")
    old_str: str = Field(..., description="Text to search for - must match exactly and must only have one match exactly")
    new_str: str = Field(..., description="Text to replace old_str with")

EDIT_FILE_INPUT_SCHEMA = GenerateSchema(EditFileInput)

def CreateNewFile(file_path: str, content: str) -> Tuple[str, Optional[Exception]]:
    try:
        directory = os.path.dirname(file_path)
        if directory and directory != "." and not os.path.exists(directory):
            os.makedirs(directory, mode=0o755, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully created file {file_path}", None
    except Exception as e:
        return "", Exception(f"failed to create file: {str(e)}")


def EditFile(input_data: Any) -> Tuple[str, Optional[Exception]]:
    try:
        edit_file_input = EditFileInput(**input_data)
        
        if not edit_file_input.path or edit_file_input.old_str == edit_file_input.new_str:
            return "", Exception("invalid input parameters")

        try:
            with open(edit_file_input.path, 'r', encoding='utf-8') as f:
                old_content = f.read()
        except FileNotFoundError:
            if edit_file_input.old_str == "":
                return CreateNewFile(edit_file_input.path, edit_file_input.new_str)
            return "", Exception("file not found")
        except Exception as e:
            return "", e

        new_content = old_content.replace(edit_file_input.old_str, edit_file_input.new_str)

        if old_content == new_content and edit_file_input.old_str != "":
            return "", Exception("old_str not found in file")

        with open(edit_file_input.path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return "OK", None
    except Exception as e:
        return "", e

EDIT_FILE_DEFINITION = ToolDefinition(
    name="edit_file",
    description="""Make edits to a text file. Replaces 'old_str' with 'new_str' in the given file. 'old_str' and 'new_str' MUST be different from each other. If the file specified with path doesn't exist, it will be created.""",
    input_schema=EDIT_FILE_INPUT_SCHEMA,
    function=EditFile,
)

if __name__ == "__main__":
    main()

