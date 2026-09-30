import mysql.connector as dbconnector

class DatabaseUtil:
    """Connect to a database and collect schema details for SQL prompts."""

    def __init__(self, db_config):
        """Initialize a database connection from the supplied configuration."""
        self.db_config = db_config

        try:
            self.connection = dbconnector.connect(**db_config)

        except Exception as e:
            print(f"Error connecting to database: {e}")
            self.connection = None

    def execute_query(self, query):
        """Execute a SQL query and return the results."""
        
        if self.connection is None:
            print(f"Error: No database connection.")
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            return results

        except Exception as e:
            print(f"Error executing query: {e}")
            return None

        finally:
            # Close the cursor and connection whether execution succeeds or fails.
            if cursor:
                cursor.close()
            if self.connection:
                self.connection.close()


    def extract_schema(self, db_name, db_engine):
        """Return schema and sample-row context, or None if not connected."""

        if self.connection is None:
            print(f"Error connecting to database")
            return None

        schema_context = ""
        cursor = self.connection.cursor()
        database = db_name
        database_engine = db_engine
        try:
            cursor.execute(f"SHOW TABLES FROM {database}")
            rows = cursor.fetchall()

            schema_context+=f"Database Engine: {database_engine}\nDatabase Name: {database}\n"

            for row in rows:
                schema_context = f"{schema_context}\nTable_name: {row[0]}\n"

                cursor.execute(f"DESCRIBE {database}.{row[0]}")
                column_list = cursor.fetchall()

                for column in column_list:
                    schema_context= f"{schema_context}\n Column: {column[0]}, Data Type: {column[1]}"

                schema_context+=f"\n\n SAMPLE DATA from table {row[0]}:"

                # A few example rows give the SQL generator context about stored values.
                cursor.execute(f"SELECT * FROM {database}.{row[0]} LIMIT 5")
                sample_data = cursor.fetchall()

                for sample in sample_data:
                    schema_context=f"{schema_context}\n {sample}"

                schema_context+="\n\n"

        except Exception as e:
            print(f"Error fetching Schema details: {e}")

        finally:
            # Release database resources even if schema extraction fails.
            if cursor:
                cursor.close()
            if self.connection:
                self.connection.close()

        return schema_context

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os
    load_dotenv()

    obj = DatabaseUtil({
        "host":os.getenv("DB_HOST"),
        "port":os.getenv("DB_PORT"),
        "user":os.getenv("DB_USERNAME"),
        "password":os.getenv("DB_PWD"),
        "database":os.getenv("DB_NAME")
    })

    # schema_details = obj.extract_schema("OLA")

    # with open("test2.txt", "w") as file:
    #     file.write(schema_details)

    query_result = obj.execute_query("SELECT model, COUNT(*) AS total_count\nFROM vehicles\nGROUP BY model;")

    with open("test3.txt", "w") as file:
        file.write(str(query_result))

    print("printed successfully")
            