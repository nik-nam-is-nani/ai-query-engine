from nl2sql_universal import generate_sql_and_execute, api_available
from nlp_preprocessor import preprocess_query
from api_nl2sql import test_api_connection

def main():
    print("[AI] Universal AI DB System Ready!")
    
    # Test and show API status
    print("\nTesting API Connection...")
    if test_api_connection():
        print("[OK] AI API Connected - Natural Language to SQL enabled!")
    else:
        print("[!] AI API not available - using fallback plugins")
    
    db = input("\nEnter DB name: ").strip()

    while True:
        q = input("\nAsk (or 'exit'): ").strip().replace('"','')
        if q.lower() == "exit":
            break
        if not q:
            continue

        clean_q = preprocess_query(q)

        sql = generate_sql_and_execute(db, clean_q)

        if sql:
            print("\nFinal SQL:\n", sql)
        else:
            print("Query handled without SQL or no result.")

if __name__ == "__main__":
    main()
