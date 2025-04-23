#!/usr/bin/env python
"""
Clean up unused tables from the database to synchronize the application.
This script identifies and removes duplicate and unused tables in the database.
"""
import os
import sys
import psycopg2
from psycopg2 import sql

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_project.settings')

import django
django.setup()

from django.conf import settings
from django.apps import apps

# Potentially unused tables (these are legacy or should be removed safely)
UNUSED_TABLES = [
    # Legacy Prisma tables
    '_prisma_migrations',
    'Keyword',
    'PaperKeyword',
    'User',  # Not Django's auth_user
]

# Tables that might have data that needs to be migrated before removal
REDUNDANT_TABLES = {
    'public_api_paper': 'users_paper',
    'public_api_dataset': 'users_dataset',
    'public_api_publication': 'users_publication',
    'public_api_interestingpaper': 'users_paper',  # Map to appropriate destination
    'public_api_dataset_papers': None,  # M2M relationship table, can be dropped safely
    'public_api_profile': 'users_userprofile',  # Map public_api profiles to user profiles
}

# Manual column mappings for handling case sensitivity and different column names
COLUMN_MAPPINGS = {
    'public_api_paper': {
        'sourceCode': 'sourcecode',  # Fix for case sensitivity
        'downloadUrl': 'file'        # Map downloadUrl to file 
    },
    'public_api_dataset': {
        'downloadUrl': None,         # Skip this column
        'paperCount': None,          # Skip this column
        'thumbnailUrl': None,        # Skip this column
        'benchmarks': None           # Skip this column
    }
}

def confirm_action(message):
    """Ask user for confirmation before proceeding"""
    response = input(f"{message} (yes/no): ").lower().strip()
    return response == 'yes'

def get_column_info(cursor, table_name):
    """Get column information for a table"""
    cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}';")
    return {row[0]: row[1] for row in cursor.fetchall()}

def check_data_existence(cursor, table_name):
    """Check if a table has any data"""
    try:
        cursor.execute(sql.SQL("SELECT COUNT(*) FROM {};").format(sql.Identifier(table_name)))
        count = cursor.fetchone()[0]
        return count > 0
    except psycopg2.Error:
        # If error occurs, rollback and return False
        cursor.connection.rollback()
        return False

def main():
    # Extract database connection info from Django settings
    db_config = settings.DATABASES['default']
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=db_config.get('NAME', 'research_assistant_db'),
        user=db_config.get('USER', 'postgres'),
        password=db_config.get('PASSWORD', 'postgres'),
        host=db_config.get('HOST', 'localhost'),
        port=db_config.get('PORT', '5432')
    )
    conn.autocommit = False  # Ensure we're in transaction mode
    
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    all_tables = [row[0] for row in cursor.fetchall()]
    
    print("Found tables in database:")
    for table in all_tables:
        print(f"  - {table}")
    
    print("\nThe following tables appear to be unused and can be safely removed:")
    tables_to_remove = []
    for table in UNUSED_TABLES:
        if table in all_tables:
            has_data = check_data_existence(cursor, table)
            tables_to_remove.append(table)
            print(f"  - {table}{' (contains data)' if has_data else ''}")
    
    print("\nThe following tables appear to be redundant and might need data migration:")
    redundant_tables_to_process = []
    for redundant_table, target_table in REDUNDANT_TABLES.items():
        if redundant_table in all_tables:
            has_data = check_data_existence(cursor, redundant_table)
            redundant_tables_to_process.append((redundant_table, target_table))
            status = "(contains data - will attempt migration)" if has_data and target_table else "(contains data - will be dropped)" if has_data else ""
            print(f"  - {redundant_table} -> {target_table if target_table else 'N/A'} {status}")
    
    if not tables_to_remove and not redundant_tables_to_process:
        print("No unused tables found to remove.")
        return
    
    if not confirm_action("\nDo you want to proceed with database cleanup?"):
        print("Operation cancelled.")
        return
    
    # First handle simple removals
    for table in tables_to_remove:
        try:
            print(f"Dropping table {table}...")
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table)))
            conn.commit()
            print(f"Successfully dropped table {table}")
        except Exception as e:
            conn.rollback()
            print(f"Error dropping table {table}: {e}")
    
    # Then handle redundant tables that might need data migration
    for redundant_table, target_table in redundant_tables_to_process:
        try:
            has_data = check_data_existence(cursor, redundant_table)
            
            if has_data and target_table:
                print(f"\nTable {redundant_table} contains data and has a target table {target_table}.")
                if confirm_action(f"Would you like to attempt data migration from {redundant_table} to {target_table}?"):
                    try:
                        # This is a simplified approach - in a real migration you'd want more sophisticated mapping
                        source_columns = get_column_info(cursor, redundant_table)
                        target_columns = get_column_info(cursor, target_table)
                        
                        # Normalize column names to lowercase for comparison
                        source_columns_lower = {k.lower(): k for k in source_columns.keys()}
                        target_columns_lower = {k.lower(): k for k in target_columns.keys()}
                        
                        # Find common columns with case-insensitive matching
                        common_columns = []
                        source_to_target_mapping = {}
                        
                        for source_col in source_columns.keys():
                            source_col_lower = source_col.lower()
                            
                            # Check if this column has a special mapping
                            if redundant_table in COLUMN_MAPPINGS and source_col in COLUMN_MAPPINGS[redundant_table]:
                                mapped_col = COLUMN_MAPPINGS[redundant_table][source_col]
                                if mapped_col:  # If not None (i.e., not to be skipped)
                                    if mapped_col.lower() in target_columns_lower:
                                        target_col = target_columns_lower[mapped_col.lower()]
                                        common_columns.append(source_col)
                                        source_to_target_mapping[source_col] = target_col
                            # Otherwise use case-insensitive matching
                            elif source_col_lower in target_columns_lower:
                                target_col = target_columns_lower[source_col_lower]
                                common_columns.append(source_col)
                                source_to_target_mapping[source_col] = target_col
                        
                        # Typically don't want to map IDs
                        if 'id' in common_columns:
                            common_columns.remove('id')
                            source_to_target_mapping.pop('id', None)
                        
                        if common_columns:
                            print(f"Found common columns: {', '.join(common_columns)}")
                            
                            # Prepare source and target column lists for the SQL query
                            source_cols_sql = ', '.join(common_columns)
                            target_cols_sql = ', '.join([source_to_target_mapping[col] for col in common_columns])
                            
                            # Insert data for common columns
                            query = f"""
                            INSERT INTO {target_table} ({target_cols_sql})
                            SELECT {source_cols_sql} FROM {redundant_table}
                            ON CONFLICT DO NOTHING;
                            """
                            
                            print(f"Running migration query...")
                            cursor.execute(query)
                            affected = cursor.rowcount
                            conn.commit()
                            print(f"Migrated {affected} rows from {redundant_table} to {target_table}")
                        else:
                            print(f"No common columns found between {redundant_table} and {target_table}")
                    except Exception as e:
                        conn.rollback()
                        print(f"Error during migration: {e}")
                        if not confirm_action("Continue with dropping the table anyway?"):
                            continue
            
            # Drop the redundant table
            print(f"Dropping redundant table {redundant_table}...")
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(redundant_table)))
            conn.commit()
            print(f"Successfully dropped table {redundant_table}")
        except Exception as e:
            conn.rollback()
            print(f"Error dropping table {redundant_table}: {e}")
    
    print("\nDatabase cleanup completed successfully!")
    
    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main() 