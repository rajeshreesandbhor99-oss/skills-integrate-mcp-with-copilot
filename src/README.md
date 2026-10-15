# Mergington High School Activities API

A super simple FastAPI application that lets visitors view extracurricular activities and teachers manage student registrations.

## Features

- View all available extracurricular activities
- Publicly view activities and their participant lists
- Let authenticated teachers sign up and unregister students
- Protect teacher credentials with PBKDF2 password hashes

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create `src/teachers.json` with teacher usernames and PBKDF2 password hashes:

   ```json
   [
     {
       "username": "teacher",
       "password_hash": "pbkdf2_sha256$600000$<salt-hex>$<hash-hex>"
     }
   ]
   ```

   Generate a hash without storing the password in the file:

   ```python
   from getpass import getpass
   import hashlib
   import secrets

   password = getpass("Teacher password: ")
   salt = secrets.token_bytes(16)
   password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
   print(f"pbkdf2_sha256$600000${salt.hex()}${password_hash.hex()}")
   ```

   Restrict the credentials file to the server account (for example,
   `chmod 600 src/teachers.json`). The credentials file is ignored by Git. To
   use a different path, set `TEACHER_CREDENTIALS_FILE`. For HTTPS deployments,
   set `COOKIE_SECURE=true`.

3. Run the application:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Publicly get all activities and participants                        |
| GET    | `/auth/me`                                                        | Check the current teacher session                                   |
| POST   | `/auth/login`                                                     | Create a teacher session using JSON username and password           |
| POST   | `/auth/logout`                                                    | End the current teacher session                                     |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (teacher session required)                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher session required)                  |

Teacher sessions are stored in memory and expire after eight hours. Restarting
the server invalidates existing sessions. Activities and registrations remain
in memory as before.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
