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
source venv/bin/activate
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

5. Set up forward port: Since our database is hosted on HUST's server, and that server doesn't expose port 5432 to the internet. We need to forward port 5432 to localhost in order to be able to access to the database. Before doing any further step, please contact [@hathubkhn](https://github.com/hathubkhn) for accessing the server. After that, run the following command:
```
ssh -f -N -L 5432:localhost:5432 hust@202.191.56.91
```
and then enter the password. Now you can access to the database on `localhost:5432`

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