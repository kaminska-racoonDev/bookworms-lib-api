from lib_app.models import Book


def create_book(
    title="1984",
    author="G. Orwell",
    cover="HARD",
    inventory=4,
    daily_fee=20.2
):
    return Book.objects.create(
        title=title,
        author=author,
        cover=cover,
        inventory=inventory,
        daily_fee=daily_fee
    )
