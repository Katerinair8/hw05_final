from django.utils.timezone import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    date = datetime.today()
    return {
        'year': date.year
    }
