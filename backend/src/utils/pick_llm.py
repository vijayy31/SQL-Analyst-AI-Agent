from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def pick_llm(level: str):
    """Return a ChatOpenAI client for the requested question-complexity level.

    Args:
        level: Case-insensitive model level: "low", "medium", or "high".

    Raises:
        ValueError: If level is not one of the supported values.
    """

    if level.lower() == "low":
        llm = ChatOpenAI(model = "gpt-6-luna")

    elif level.lower() == "medium":
        llm = ChatOpenAI(model = "gpt-6-sol")

    elif level.lower() == "high":
        llm = ChatOpenAI(model = "gpt-5.6-sol")

    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm

if __name__ == "__main__":
    # Manual example for checking model selection and invocation.
    agent = pick_llm("medium")

    print(agent)
    response = agent.invoke("Describe breifly about SAM ALTMAN")

    print(response)
