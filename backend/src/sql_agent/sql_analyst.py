import os
import sys
# sys.path.append("..")
from dotenv import load_dotenv
from Schema.Schema import AgentSchema
from utils.pick_llm import pick_llm
from utils.databaseConn import DatabaseUtil
from langchain_core.messages import HumanMessage, AIMessage
load_dotenv()
def generate_curated_ques(state: AgentSchema) -> AgentSchema:

    """Refine the user's question and store it in the agent state and messages."""
    user_question = state.user_question
    
    llm = pick_llm("low")
    response = llm.invoke(f"Curate the following question: {user_question}")
    
    state.curated_ques = response.content
    state.messages = state.messages + [
        HumanMessage(content=user_question),
        AIMessage(content=response.content),
    ]

    return state

def generate_query_context(state: AgentSchema) -> AgentSchema:
    """Extract the database schema and store it as SQL-generation context."""

    db_config = {
        "host":os.getenv("DB_HOST"),
        "port":os.getenv("DB_PORT"),
        "user":os.getenv("DB_USERNAME"),
        "password":os.getenv("DB_PWD"),
        "database":os.getenv("DB_NAME")
    }

    db_obj = DatabaseUtil(db_config)

    db_engine = os.getenv("DB_ENGINE")
    db_name = os.getenv("DB_NAME")

    state.prompt_query_context = db_obj.extract_schema( db_name=db_name, db_engine=db_engine)

    return state

def generate_sql_query(state: AgentSchema):
    """Generate a read-only SQL query from the curated question and schema."""

    curated_question = state.curated_ques
    schema_context = state.prompt_query_context

    prompt = f"""You are an expert SQL query generator.
    
    Your task is to convert the user's natural language question into a valid MySQL SQL query.

    You will be provided with:
    1. Database schema
    2. User's question

    Rules:
    - Generate only the SQL query.
    - Do not provide explanations.
    - This agent supports read-only Data Query Language (DQL) requests only.
    - If the user asks to change database data or structure, including INSERT, UPDATE, DELETE, DROP, ALTER, or TRUNCATE, return exactly INVALID_QUERY.
    - Do not reinterpret a data-modifying request as a SELECT query.
    - Use only tables and columns that exist in the provided schema.
    - Do not invent tables or columns.
    - Use valid MySQL syntax.
    - Use appropriate JOINs when data is required from multiple tables.
    - Use WHERE conditions when required.
    - Use GROUP BY, HAVING, ORDER BY, and LIMIT when appropriate.
    - If the question asks for the top/bottom N records, use LIMIT.
    - Do not use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or other data-modifying statements.
    - If the request is ambiguous or cannot be answered using the schema, return exactly INVALID_QUERY.
    - For every other request, generate one read-only SELECT query and nothing else.

    Database Schema:
    {schema_context}

    User Question:
    {curated_question}
    """

    agent = pick_llm("Medium")

    response = agent.invoke(prompt)

    state.generated_sql_query = response.content
    state.messages = state.messages + [AIMessage(content=response.content)]
    state.retry_count= state.retry_count+ 1

    return state

def check_is_safe(state: AgentSchema):
    """Classify the generated SQL and record its safety and command type."""

    from langchain_typesafe import TypeSafeClassifier, Noul, Choice

    classifier = TypeSafeClassifier()
    generated_sql_query = state.generated_sql_query

    response = classifier.invoke({
        "state": generated_sql_query,
        "questions": {
            "is_dql": Noul(
                instructions="Does this generated sql query use data query language?"
                ),
            "is_safe": Noul(
                instructions="is the generated query is safe to run in database? Will it not modify the data in database?"
                ),
            "sql_type": Choice(
                instructions="What type of SQL command is this?",
                criteria={
                            "Its Data query language": "If it is Data query language",
                            "Its not belong to data query language": "If it is anything else other than the DQL"
                            }
                    )   
            }
    })
    res = response.model_dump()
    state.is_safe = res["answers"]["is_safe"]["noul"]
    state.comments = res["answers"]["sql_type"]["choice"]

    return state


def check_generated_query(state: AgentSchema):
    """Assess whether the generated SQL answers the user's curated question."""

    curated_ques = state.curated_ques
    generated_query = state.generated_sql_query

    from langchain_typesafe import TypeSafeClassifier, Noul, Choice

    classifier = TypeSafeClassifier()

    response = classifier.invoke({
        "state": f"user_question: {curated_ques},\ngenerated_sql_query: {generated_query}",
        "questions": {

            "result_correct":Noul( instructions="""
                        Would executing the generated SQL produce the result
                        the user is asking for?

                        Judge semantic correctness rather than textual similarity.
                        Equivalent SQL formulations should be considered correct.

                        """)
            }
        }
    )

    res = response.model_dump()
    state.is_correct_query = "Yes" if res["answers"]["result_correct"]["noul"] > 0.5 else "No"

    return state

def execute_query(state: AgentSchema):
    """Execute the generated SQL query and store the results in the agent state."""

    db_config = {
        "host":os.getenv("DB_HOST"),
        "port":os.getenv("DB_PORT"),
        "user":os.getenv("DB_USERNAME"),
        "password":os.getenv("DB_PWD"),
        "database":os.getenv("DB_NAME")
    }

    db_obj = DatabaseUtil(db_config)

    sql_query = state.generated_sql_query

    result = db_obj.execute_query(sql_query)

    state.query_execution_result = str(result)

    return state

def generate_final_answer(state: AgentSchema):
    """Generate a final answer based on the user's question, the generated SQL, and the query results."""

    user_question = state.user_question
    generated_sql_query = state.generated_sql_query
    query_execution_result = state.query_execution_result
    is_safe = state.is_safe
    comments = state.comments

    prompt = f"""You are an expert SQL analyst.

    Your task is to provide a final answer to the user's question using the agent state and query results.

    You will be provided with:
    1. User's question
    2. Generated SQL query
    3. Query execution results

    Rules:
    - Provide a concise and clear answer to the user's question.
    - Start with a short, plain-language summary and one useful takeaway that is directly supported by the query results.
    - For comparisons or grouped totals, present the values in a Markdown table; never put a table inline in a paragraph.
    - Preserve the values and categories from the query results. Do not invent trends, causes, units, or conclusions unsupported by the data.
    - Do not include the SQL query or execution results in your answer.
    - If the query execution result is empty or indicates no data, inform the user accordingly.
    - If the generated query is INVALID_QUERY, the query is not safe, or its command type is not DQL, do not claim that it ran and do not present query results.
    - For those unsupported requests, clearly say that this agent only runs read-only SELECT queries and cannot make changes to the database.
    - Suggest one relevant read-only question the user could ask instead. For example, for a request to delete the UPI payment method, say: "I can't delete payment methods because I only run read-only queries. You can ask me to show which payment methods are used or calculate the total paid using UPI."
    - If limit is not mentioned in the user question, use the limit as 10 retrieve the new data 
    from the database using timestamp and provide the answer to the user.

    User Question:
    {user_question}

    Generated SQL Query:
    {generated_sql_query}

    is safe to query from db: {is_safe} and the comment from the agent {comments}

    Query Execution Result:
    {query_execution_result}
    """

    agent = pick_llm("Medium")

    response = agent.invoke(prompt)

    state.final_answer = response.content
    state.messages = state.messages + [AIMessage(content=response.content)]

    return state

def decide_safe_query(state: AgentSchema):

    is_safe = state.is_safe

    if is_safe > 0.6:
        return "pass"

    else:
        return "fail"

def decide_generated_query(state:AgentSchema):

    correct = state.is_correct_query
    if state.retry_count >=2:
        return "end"
    
    elif correct == "Yes":
        return "pass"
    else:
        return "fail"

from langgraph.graph import StateGraph, START, END

graph = StateGraph(AgentSchema)

graph.add_node("generate_curated_ques", generate_curated_ques)
graph.add_node("generate_query_context", generate_query_context)
graph.add_node("generate_sql_query", generate_sql_query)
graph.add_node("check_is_safe", check_is_safe)
graph.add_node("check_generated_query", check_generated_query)
graph.add_node("execute_query", execute_query)
graph.add_node("generate_final_answer", generate_final_answer)

graph.add_edge(START, "generate_curated_ques")
graph.add_edge("generate_curated_ques", "generate_query_context")
graph.add_edge("generate_query_context", "generate_sql_query")
graph.add_edge("generate_sql_query", "check_is_safe")

graph.add_conditional_edges("check_is_safe", decide_safe_query, {
    "pass":"check_generated_query",
    "fail": "generate_final_answer"
    }
)
graph.add_conditional_edges("check_generated_query", decide_generated_query,{
    "pass": "execute_query",
    "fail": "generate_sql_query",
    "end": "generate_final_answer"
})
graph.add_edge("execute_query", "generate_final_answer")

graph.add_edge("generate_final_answer", END)

app = graph.compile()
