import streamlit as st
from code_editor import code_editor
import sqlite3
import pandas as pd

ALL_TASKS: dict[str, callable] = {}


class SQLPage:
    def __init__(self, name: str):
        self.name = name

    def __call__(self, func: callable):
        def wrapper(*args, **kwargs):
            st.title(self.name)
            func(*args, **kwargs)

        ALL_TASKS[self.name] = wrapper
        return wrapper


def display_editor(key: str):
    response = code_editor(
        code="",
        lang="sql",
        height=300,
        response_mode=["debounce", "blur"],
        key=f"code_editor_{key}",
    )

    @st.cache_resource(hash_funcs={dict: lambda _response: _response.get("id")})
    def _handle_editor_change(code_editor_response):
        text = code_editor_response.get("text", "")
        st.session_state[key] = text

    _handle_editor_change(response)

    return lambda: st.session_state.get(key, "")


# https://stackoverflow.com/a/44957247/7095554
def df_column_uniquify(df):
    df_columns = df.columns
    new_columns = []
    for item in df_columns:
        counter = 0
        newitem = item
        while newitem in new_columns:
            counter += 1
            newitem = "{}_{}".format(item, counter)
        new_columns.append(newitem)
    df.columns = new_columns
    return df


def initialize_sql_session_in_memory() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # Create a sample table for demonstration
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    cursor.execute("INSERT INTO users (name, age) VALUES ('Alice', 30), ('Bob', 25)")
    conn.commit()
    return conn


def display_sql_results(conn: sqlite3.Connection, sql: str):
    if not sql.strip():
        st.warning("Please enter a SQL query to execute.")
        return
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        df = pd.DataFrame(results, columns=col_names)
        st.success("Query executed successfully!")
        st.dataframe(df_column_uniquify(df))
    except sqlite3.Error as e:
        st.error(f"An error occurred: {e}")
    finally:
        cursor.close()


def load_df(table_name: str) -> pd.DataFrame:
    return pd.read_csv(f"data/{table_name}.csv")


def display_table(table_name: str):
    df = load_df(table_name)
    st.markdown(f"## Data from table `{table_name}`")
    st.dataframe(df)


def insert_df_into_sqlite(conn: sqlite3.Connection, df: pd.DataFrame, table_name: str):
    df.to_sql(table_name, conn, if_exists='replace', index=False)


def load_hr_data(conn: sqlite3.Connection):
    for table_name in ["Employees", "Departments", "Jobs"]:
        df = load_df(table_name)
        insert_df_into_sqlite(conn, df, table_name)


def validate_sql_query(conn, user_query: str, expected_query: str, ordered: bool = True) -> bool:
    """
    Run two SQL queries and compare their results.
    """
    if not user_query.strip() or not expected_query.strip():
        return False
    try:
        user_df = pd.read_sql_query(user_query, conn)
        expected_df = pd.read_sql_query(expected_query, conn)

        if ordered:
            return user_df.equals(expected_df)
        else:
            return user_df.sort_values(by=list(user_df.columns)).reset_index(drop=True).equals(
                expected_df.sort_values(by=list(expected_df.columns)).reset_index(drop=True)
            )
    except Exception as e:
        st.error(f"Error executing queries: {e}")
        return False


@SQLPage("Welcome")
def display_welcome():
    st.markdown("""
    # Welcome to the SQL Tutorial App
    This app will guide you through various SQL tasks and concepts.
    Use the sidebar to navigate through different tasks.
    
    ## What is a Relational Database?
    
    A relational database is a type of database that stores data in tables, which are structured in rows and columns.
    Each table represents a different entity, and relationships can be established between tables using keys.
    You can think about it like an Excel spreadsheet, where each sheet is a table, and you can link data across sheets.
    Each spreadsheet can have multiple rows and columns.
    Example tables in a relational database might include `Employees`, `Departments`, and `Jobs`.
    
    """)
    display_table("Employees")
    display_table("Departments")
    display_table("Jobs")


@SQLPage("Lesson 1: SELECT Query")
def task_1():
    st.markdown("""
    In this lesson, you will learn how to write a basic SQL query to select data from a table.
    The following SQL query retrieves all records from the `users` table:
    ```sql
    SELECT * FROM users;
    ```
    Use the SQL editor below to write your query.
    """)
    conn = initialize_sql_session_in_memory()
    load_hr_data(conn)
    get_welcome_key = display_editor("welcome_sql")
    if st.button("Run Query"):
        sql = get_welcome_key()
        display_sql_results(conn, sql)

    st.header("Task 1: Write a SELECT Query")
    st.markdown("""
    Write a SQL query to select all columns from the `Employees` table.
    """)
    get_task1_key = display_editor("task_1_sql")
    if st.button("Run Task 1 Query"):
        task_1_sql = get_task1_key()
        display_sql_results(conn, task_1_sql)
        if validate_sql_query(conn, task_1_sql, "SELECT * FROM Employees"):
            st.success("Correct! You have successfully written a SELECT query.")
        else:
            st.error("Incorrect answer. Please try again.")


def main_page():
    st.set_page_config(page_title="SQL Tutorial", layout="wide")
    page_name_to_funcs = ALL_TASKS
    st.sidebar.title("Select the task")
    page = st.sidebar.selectbox("Select a page", list(page_name_to_funcs.keys()))
    page_name_to_funcs[page]()


if __name__ == "__main__":
    main_page()
