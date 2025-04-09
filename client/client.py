import asyncio
import logging
from typing import Optional
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dotenv import load_dotenv

from llm import LLMClient

load_dotenv()  # load environment variables from .env
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MCPClient:
    def __init__(self, llm: LLMClient):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = llm

    async def _set_tools(self):
        self.tools_list = await self.session.list_tools()
        self.available_tools = [{ 
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in self.tools_list.tools]

    async def connect_to_server(self):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        command = "python"
        server_params = StdioServerParameters(
            command=command,
            args=[str(Path(__file__).parent.parent / "server/main.py")],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # Available tools
        await self._set_tools()
        print("\nConnected to server with tools:", [tool.name for tool in self.tools_list.tools])

    def _get_args_desc(self, input_schema):
        args_desc = []
        if "properties" in input_schema:
            for param_name, param_info in input_schema["properties"].items():
                arg_desc = (
                    f"- {param_name}: {param_info.get('description', 'No description')}"
                )
                if param_name in input_schema.get("required", []):
                    arg_desc += " (required)"
                args_desc.append(arg_desc)
        return args_desc

    def _get_system_message(self):
            tools_description = ""
            for tool in self.tools_list.tools:
                args_desc = self._get_args_desc(tool.inputSchema)
                tools_description += (
                    f"\nTool: {tool.name}"
                    f"Description: {tool.description}"
                    "Arguments:"
                    f"{chr(10).join(args_desc)}"
                )

            return (
                "You are a helpful assistant with access to these tools:\n\n"
                f"{tools_description}\n"
                "Choose the appropriate tool based on the user's question. "
                "If no tool is needed, reply directly.\n\n"
                "IMPORTANT: When you need to use a tool, you must ONLY respond with "
                "the exact JSON object format below, nothing else:\n"
                "{\n"
                '    "tool": "tool-name",\n'
                '    "arguments": {\n'
                '        "argument-name": "value"\n'
                "    }\n"
                "}\n\n"
                "After receiving a tool's response:\n"
                "1. Transform the raw data into a natural, conversational response\n"
                "2. Keep responses concise but informative\n"
                "3. Focus on the most relevant information\n"
                "4. Use appropriate context from the user's question\n"
                "5. Avoid simply repeating the raw data\n\n"
                "Please use only the tools that are explicitly defined above."
            )

    async def process_llm_response(self, llm_response: str, _id) -> str:
        """Process the LLM response and execute tools if needed.

        Args:
            llm_response: The response from the LLM.

        Returns:
            The result of tool execution or the original response.
        """
        import json
        from ast import literal_eval
        try:
            tool_call = json.loads(llm_response)
        except json.JSONDecodeError:
            try:
                tool_call = literal_eval(llm_response)
                tool_call["arguments"] = literal_eval(tool_call["arguments"])
            except:
                return None, None

        if "tool" in tool_call and "arguments" in tool_call:
            logging.info(f"Executing tool: {tool_call['tool']}(**{tool_call['arguments']})")
            tools = self.tools_list.tools
            if any(tool.name == tool_call["tool"] for tool in tools):
                result = await self.session.call_tool(
                    tool_call["tool"], tool_call["arguments"]
                )
                logging.info(f"Tool Output: {result.content}")

                tool_output = {
                    "name": tool_call["tool"],
                    "content": str(result.content),
                    "role": "tool",
                    "tool_call_id": _id,
                }
                tool_call = {
                    "role": "assistant",
                    "tool_calls": [{"function": {
                        "name": tool_call["tool"], "arguments": tool_call["arguments"]
                    }, "id": _id}]
                }
                return tool_call, tool_output
            raise ValueError(f"No server found with tool: {tool_call['tool']}")
        return None, None

    async def process_query(self, query: str) -> str:
        """Process a query using LLM and available tools"""
        messages = [
            {
                "role": "system",
                "content": self._get_system_message()
            },
            {
                "role": "user",
                "content": query
            }
        ]

        # Initial LLM API call
        for i in range(5):
            response = self.llm.get_response(messages)
            tool_call, tool_output = await self.process_llm_response(response, str(i) * 9)
            if tool_call is None:
                messages.append({"role": "assistant", "content": response})
                break
            else:
                messages.append(tool_call)
                messages.append(tool_output)

        return messages[-1]["content"]

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print(
            "Ask questions about the weather at a city (by city name or by person name)."
            "or type 'quit' to exit."
        )

        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == "quit":
                break

            response = await self.process_query(query)
            print("\n" + response)

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    client = MCPClient(llm=LLMClient())
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys
    asyncio.run(main())
