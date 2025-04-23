# Database Cleanup

This document describes the database cleanup performed to remove redundant and unused tables.

## Summary

We identified and removed 10 unnecessary tables from the database:

1. Legacy Prisma tables:
   - `_prisma_migrations` - Legacy migration table used by Prisma ORM
   - `Keyword` - Unused keyword table 
   - `PaperKeyword` - Unused relation table
   - `User` - Duplicate of Django's `auth_user`

2. Redundant tables from the `public_api` app:
   - `public_api_paper` - Duplicate of `users_paper`
   - `public_api_dataset` - Duplicate of `users_dataset`
   - `public_api_dataset_papers` - Many-to-many relationship table
   - `public_api_publication` - Duplicate of `users_publication`
   - `public_api_interestingpaper` - Relation table
   - `public_api_profile` - Duplicate of `users_userprofile`

## Cleanup Process

The cleanup process involved:

1. Identifying unused and redundant tables in the database
2. Attempting to migrate data from redundant tables to their counterparts
3. Safely dropping tables after confirmation

## Tools

A cleanup script was created at `backend/scripts/clean_database.py` that:
- Examines the database structure
- Identifies tables for cleanup
- Attempts data migration where possible
- Safely removes unused tables

To run the cleanup script:
```
cd backend
chmod +x clean_database.sh
./clean_database.sh
```

## Future Considerations

1. The application currently has a `public_api` app with models that duplicate those in the `users` app. Consider consolidating these models to avoid future redundancy.

2. Make sure all database operations use Django's migrations system to keep the database schema in sync with the application code.

3. Regularly review the database schema to identify and remove unused tables as the application evolves. 