import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    date = datetime.datetime.today()
    return {
        'year': date.year
    }
