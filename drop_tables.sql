-- SQL script to drop the specified tables
-- Handle foreign key constraints by dropping tables in the correct order

-- First drop tables with foreign keys
DROP TABLE IF EXISTS public_api_interestingpaper CASCADE;
DROP TABLE IF EXISTS users_datasetreference CASCADE;
DROP TABLE IF EXISTS public_api_dataset_papers CASCADE;

-- Then drop the main tables
DROP TABLE IF EXISTS public_api_dataset CASCADE;
DROP TABLE IF EXISTS users_dataset CASCADE;
DROP TABLE IF EXISTS public_api_paper CASCADE;
DROP TABLE IF EXISTS users_paper CASCADE;
DROP TABLE IF EXISTS users_profile CASCADE;
DROP TABLE IF EXISTS public_api_profile CASCADE;
DROP TABLE IF EXISTS users_publication CASCADE;
DROP TABLE IF EXISTS public_api_publication CASCADE; 