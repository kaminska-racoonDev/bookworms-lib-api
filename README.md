# Bookworms Library API
A browsable API for local library management.

![Bookworms Library Logo](https://raw.githubusercontent.com/kaminska-racoonDev/bookworms-lib-api/develop/cover.png)

## Features of the API:
- create and add new books to library catalogue
- keep track of each book's inventory (amount of books available for borrowing)
- set individual daily fees for borrowing each book
- automatic creation of fines and payments for borrowings by defined formula
- forbid users from borrowing new books if they have pending payments or fines
- manage books and borrowings through admin access
- filter borrowings by status

## Local API setup
1. Clone or fork repo through GitHub desktop or via command line
2. Create virtual environment
3. Run `pip install -r requirements.txt` to install needed packages
4. Copy `.env.example` to `.env` and fill in the required values
5. In `.env` (or `settings.py`, depending on your setup), set `DEBUG` and `ALLOWED_HOSTS`:
   - For local development: `DEBUG=True` and `ALLOWED_HOSTS=127.0.0.1,localhost`
   - For production/deployment: `DEBUG=False` and set `ALLOWED_HOSTS` to your actual domain(s)
6. Run `python manage.py migrate` to apply database migrations
7. Run `python manage.py createsuperuser` to create an admin account for adding books into the system
8. Run `python manage.py runserver` to boot up local server on "http://127.0.0.1:8000/" as base link
9. Optionally you can load mock data from `fixture.json` file by running `python manage.py loaddata fixture.json`
10. You can run tests by using `python manage.py test` command

## Endpoints:
1. `admin/` - Admin panel
2. `api/v1/user/` - User management (registration, login, account)
    2.1. `me/` - Account view
    2.2. `login/` - Authentication for registered user
    2.3. `register/` - Registration of new user
    2.4. `token/refresh/` - Generating new token when last one's session has ended
3. `api/v1/lib_app/`
    3.1. `book/` - Book list
    3.2. `borrowing/` - Borrowing list
        3.2.1 `return/` - Return borrowing
    3.3. `payments/` - Payment list
4. `api/v1/doc/` - downloadable documentation that may be used in Postman
5. `api/v1/doc/swagger/` - Swagger documentation
6. `api-auth/` - Registration for testing in Browsable API used in development

## Database structure
It might be useful to reference the structure for potential improvements and developing additional features.
![DB structure diagram](https://raw.githubusercontent.com/kaminska-racoonDev/bookworms-lib-api/develop/Bookworms%20Library%20API.drawio.png)

---
### Feedback

This project still has a lot of potential and might need more work. If anyone spots an issue, error or potential improvement that may be added feel free to reach out, create an issue or make a pull request to the original repo.
All constructive feedback is welcomed! 🤗❤