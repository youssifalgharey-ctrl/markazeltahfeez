# Auth API — Spring Boot JWT Authentication

A clean, production-style REST API for user registration and login using
**Spring Boot 3**, **Spring Security**, **JWT**, and **JPA/H2**.

Built as a portfolio project to demonstrate backend fundamentals: layered
architecture, password hashing, stateless authentication, input validation,
and centralized error handling.

## Features

- User registration with hashed passwords (BCrypt — passwords are never stored in plain text)
- Login that returns a signed JWT
- A protected endpoint (`/api/auth/me`) that only works with a valid token
- Input validation (email format, password length, required fields)
- Centralized error handling — clean JSON error responses instead of stack traces
- In-memory H2 database — runs immediately with zero setup

## Tech Stack

| Layer          | Technology                  |
|----------------|------------------------------|
| Language       | Java 17                     |
| Framework      | Spring Boot 3.3              |
| Security       | Spring Security + JWT (jjwt) |
| Database       | H2 (in-memory) + Spring Data JPA |
| Build Tool     | Maven                        |

## Project Structure

```
src/main/java/com/example/authapi/
├── model/          User entity (implements Spring Security's UserDetails)
├── repository/     Data access (Spring Data JPA)
├── dto/            Request/response objects
├── security/       JWT creation, parsing, and the request filter
├── service/        Business logic (register/login)
├── controller/      REST endpoints
└── config/          Security rules + global exception handling
```

## Running It

```bash
mvn spring-boot:run
```

The API starts on `http://localhost:8080`.

## API Endpoints

### Register
```
POST /api/auth/register
Content-Type: application/json

{
  "fullName": "Youssef Ahmed",
  "email": "youssef@example.com",
  "password": "secret123"
}
```
Returns a JWT + user info.

### Login
```
POST /api/auth/login
Content-Type: application/json

{
  "email": "youssef@example.com",
  "password": "secret123"
}
```
Returns a JWT.

### Protected route (requires the token from register/login)
```
GET /api/auth/me
Authorization: Bearer <token>
```

## Testing with curl

```bash
# Register
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"fullName":"Youssef","email":"y@test.com","password":"secret123"}'

# Login
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"y@test.com","password":"secret123"}'

# Access protected route (replace TOKEN with the value returned above)
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer TOKEN"
```

## Notes Before Using in a Real Client Project

- Change `jwt.secret` in `application.properties` to a random, private value.
- Swap H2 for PostgreSQL/MySQL in real deployments (just change the datasource config).
- Add rate limiting on `/register` and `/login` in production to prevent abuse.
