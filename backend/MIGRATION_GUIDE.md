# Database Migration Guide

## Overview
This guide explains how to run database migrations for the BAR Community Map Sharing Portal.

## Prerequisites

1. **PostgreSQL Database** must be running and accessible
2. **Python Dependencies** installed (see requirements.txt)
3. **Environment Variables** configured in `.env` file

## Environment Setup

### 1. Create .env file
Copy the example environment file and update with your database credentials:

```bash
cp .env.example .env
```

Update the `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://bar_maps_user:your_password@localhost:5432/bar_maps_db
```

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

## Running Migrations

### Option 1: Using Docker Compose (Recommended)

The docker-compose.yml automatically runs migrations when starting the backend service:

```bash
# Start all services (database + backend with auto-migration)
docker-compose up -d

# View migration logs
docker-compose logs backend | grep "Running migrations"

# Stop services
docker-compose down
```

### Option 2: Manual Migration with Alembic

If you're running PostgreSQL locally or in a separate container:

```bash
cd backend

# Check current migration status
alembic current

# Apply all pending migrations
alembic upgrade head

# Verify tables were created
python -c "from database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

Expected output should include:
```python
['users', 'maps', 'ratings', 'comments', 'alembic_version']
```

## Migration Files

### Current Migrations
- **001_initial.py** - Creates initial schema (users, maps, ratings, comments tables)

### Migration Structure
```
backend/alembic/
├── versions/
│   └── 001_initial.py      # Initial migration
├── env.py                  # Migration environment configuration
└── script.py.mako          # Template for new migrations
```

## Verifying Migration Success

### 1. Check Migration Status
```bash
cd backend
alembic current
```
Expected output: `(head)` or current revision ID

### 2. List Database Tables
```bash
cd backend
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('\n'.join(inspector.get_table_names()))"
```

### 3. Verify Table Schema
```bash
cd backend
python -c "from database import engine; from sqlalchemy import inspect; inspector = inspect(engine); print('\nUsers table columns:'); [print(f'  - {col[\"name\"]}: {col[\"type\"]}') for col in inspector.get_columns('users')]"
```

## Troubleshooting

### Migration fails with "database does not exist"
Create the database first:
```bash
# Using PostgreSQL
createdb bar_maps_db

# Or using psql
psql -U postgres -c "CREATE DATABASE bar_maps_db;"
```

### Migration fails with "connection refused"
Ensure PostgreSQL is running:
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Or with Docker
docker ps | grep postgres
```

### Migration fails with "permission denied"
Check database credentials in `.env` match the database user permissions:
```bash
# Test connection
psql -U bar_maps_user -d bar_maps_db -h localhost
```

### Want to start fresh?
Drop and recreate all tables:
```bash
cd backend

# Rollback all migrations
alembic downgrade base

# Re-apply migrations
alembic upgrade head
```

## Creating New Migrations

After modifying models in `models.py`, create a new migration:

```bash
cd backend

# Auto-generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file
# Edit: alembic/versions/YYYY_MM_DD_HHMM_revision_description.py

# Apply the new migration
alembic upgrade head
```

## Database Schema Summary

### Tables Created

1. **users**
   - User authentication and profiles
   - Fields: id, username, email, hashed_password, is_active, timestamps

2. **maps**
   - BAR map metadata and file references
   - Fields: id, name, description, author, version, creator_id, BAR-specific fields, generation params, statistics, timestamps

3. **ratings**
   - User ratings for maps (1-5 stars)
   - Fields: id, user_id, map_id, rating, timestamps

4. **comments**
   - User comments on maps
   - Fields: id, user_id, map_id, content, timestamps

### Indexes Created

- Unique indexes on users.username and users.email
- Composite index on maps(size, terrain_type)
- Composite index on maps(average_rating, rating_count)
- Indexes on foreign keys for query optimization

## Production Notes

1. **Always backup database before running migrations in production**
2. **Review auto-generated migrations before applying**
3. **Test migrations in staging environment first**
4. **Keep migration files in version control**
5. **Never modify existing migration files** - create new ones instead

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [FastAPI Database Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)
