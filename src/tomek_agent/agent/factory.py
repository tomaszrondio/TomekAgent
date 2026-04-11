from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from deepagents import create_deep_agent

from tomek_agent.agent.prompts import SYSTEM_PROMPT
from tomek_agent.agent.tools import get_current_time
from tomek_agent.config import Settings


def create_agent(settings: Settings, checkpointer: BaseCheckpointSaver, store: BaseStore):
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        max_tokens=settings.max_tokens,
        default_headers={
            "HTTP-Referer": "https://tomekagent.local",
            "X-Title": "TomekAgent",
        },
    )

    # create_deep_agent already includes by default:
    # TodoListMiddleware, FilesystemMiddleware, SummarizationMiddleware, PatchToolCallsMiddleware
    return create_deep_agent(
        model=llm,
        tools=[get_current_time],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        store=store,
    )
