# Assistant Research Backend

Backend server for the Assistant Research project, built with Django.

## Setup

### Prerequisites
- Python 3.8+
- PostgreSQL

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/assistant-research-backend.git
cd assistant-research-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit the .env file with your configuration
```

5. Set up the database:
```bash
./setup_databases.sh
```

6. Run migrations:
```bash
python manage.py migrate
```

7. Start the server:
```bash
./run_server.sh
# Or directly with:
# python manage.py runserver
```

## API Documentation

API endpoints are documented in the `docs` directory.

## Development

### Project Structure
- `auth_project/`: Authentication app
- `users/`: User management app
- `public_api/`: Main API endpoints
- `scripts/`: Utility scripts
- `data/`: Data files for import/export

### Running Tests
```bash
python manage.py test
```

## Deployment

See `docs/deployment.md` for deployment instructions. 