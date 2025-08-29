# Database Integration Setup Guide

This guide helps resolve the "relation 'guitars' does not exist" error and sets up the database integration for the Guitar Registry project.

## Quick Fix for the Error

If you're seeing errors like:
```
relation "guitars" does not exist
```

Follow these steps:

### 1. Create Environment Configuration
```bash
python setup_database.py --create-env
```

### 2. Update Database Credentials
Edit the `.env` file with your PostgreSQL credentials:
```bash
# Replace placeholder values with actual credentials
GUITAR_REGISTRY_DB_URL=postgresql://your_username:your_password@localhost:5432/guitar_registry
```

### 3. Set Up Database Schema
```bash
python setup_database.py --setup-all
```

### 4. Test the Integration
```bash
python test_db_integration.py
```

## What Was Fixed

The original error occurred because:
1. **Missing Database Schema**: The code expected a `guitars` table that didn't exist
2. **Poor Error Handling**: Database errors weren't handled gracefully
3. **Incomplete Setup Instructions**: No clear setup process for developers

## Solutions Implemented

### 1. Database Schema Verification
- Complete PostgreSQL schema with `guitars` and `manufacturers` tables
- Sample data for testing manufacturer normalization
- Proper indexes for performance
- Data validation constraints

### 2. Improved Error Handling (`db_tools.py`)
- Check if tables exist before querying
- Detect placeholder values in connection strings
- Helpful error messages with troubleshooting steps
- Graceful degradation when database unavailable

### 3. Automated Setup Script (`setup_database.py`)
- One-command database setup
- Connection testing
- Schema creation
- Integration testing
- Environment file management

### 4. Enhanced Test Script (`test_db_integration.py`)
- Better error handling for missing database
- Clear setup instructions in output
- Individual test isolation
- Helpful debugging information

### 5. Updated Documentation (`DATABASE_INTEGRATION.md`)
- Step-by-step setup instructions
- Troubleshooting guide for common issues
- Multiple setup options (automated vs manual)
- Testing procedures

## Files Added/Modified

### New Files
- The database schema should already exist in the guitar_registry database
- `setup_database.py` - Automated setup and testing script
- `.env.example` - Environment configuration template
- `README_DATABASE_SETUP.md` - This setup guide

### Modified Files
- `db_tools.py` - Enhanced error handling and table existence checks
- `test_db_integration.py` - Better error handling and user guidance
- `DATABASE_INTEGRATION.md` - Updated with setup instructions

## Testing the Fix

Run these commands to verify everything works:

```bash
# Test database connection
python setup_database.py --check-connection

# Verify schema exists
python setup_database.py --check-tables

# Test database integration tools
python setup_database.py --test-integration

# Run full test suite
python test_db_integration.py
```

## Expected Output After Fix

When tests run successfully, you should see:
```
✅ Database connection established
✅ 'guitars' table exists with N records
✅ 'manufacturers' table exists with N records
✅ Database integration test successful
```

## Troubleshooting

If you still see errors:

1. **PostgreSQL not running**: Start PostgreSQL service
2. **Database doesn't exist**: Create `guitar_registry` database
3. **Wrong credentials**: Check `.env` file values
4. **Permission issues**: Ensure database user has proper permissions

For detailed troubleshooting, see `DATABASE_INTEGRATION.md`.

## Development Notes

- Database integration is optional (controlled by `ENABLE_DB_TOOLS`)
- Agent works without database if integration fails
- All database operations are asynchronous
- Connection pooling used for performance
- Fuzzy matching for manufacturer name normalization