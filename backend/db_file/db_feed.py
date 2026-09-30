import mysql.connector as dbconnector
import polars as pl
from polars import *
from dotenv import load_dotenv
import os

load_dotenv()

def db_feed():

    # dbconnection
    conn = dbconnector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("DB_PWD"),
            database=os.getenv("DB_NAME")
        )
    
    try:
        # creating the list for the filenames
        files = ["ratings", "payments", "rides", "users", "vehicles"]

        for file in files:
            # path for the file
            file_path = os.path.join(os.path.dirname(os.getcwd()), "data",f"{file}.csv")

            # read the file using polars
            df = pl.read_csv(file_path)

            # converting the received dataframe into rows for executing cursor sql-commands
            rows = [row for row in df.iter_rows()]

            #creating cursor instance
            cursor = conn.cursor()

            #getting the columns available and the # of %s to be used
            columns = [f"{column}" for column, dtypes in df.schema.items()]
            print_s = ["%s" for column in df.schema.items()]

            #creating the sql command for the insertion
            sql_command = f"INSERT INTO OLA.{file} ({",".join(columns)})\
                                VALUES ({",".join(print_s)})"
            # cursor execution
            cursor.executemany(sql_command, rows)

            # transaction should be committed so that it ll reflect in db
            conn.commit()

            print("Data inserted successfully")
            
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # closing the connection
        cursor.close()
        conn.close()

if __name__ == "__main__":

    db_feed()