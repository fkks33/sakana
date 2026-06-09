import calendar
from datetime import datetime, timedelta, timezone

def get_jst_now():
    """Returns the current datetime in JST."""
    JST = timezone(timedelta(hours=9))
    return datetime.now(JST)

def get_one_month_later(today):
    """Calculates exactly one month later from the given date."""
    next_month_year = today.year
    next_month = today.month + 1
    if next_month > 12:
        next_month_year += 1
        next_month = 1
    
    max_day = calendar.monthrange(next_month_year, next_month)[1]
    next_month_day = min(today.day, max_day)
    return today.replace(year=next_month_year, month=next_month, day=next_month_day)

def filter_target_dates(date_strings):
    """Filters date strings (YYYYMMDD) that are between today and one month later."""
    today = get_jst_now().date()
    one_month_later = get_one_month_later(today)
    
    valid_dates = []
    for d_str in date_strings:
        d_date = datetime.strptime(d_str, "%Y%m%d").date()
        if today <= d_date <= one_month_later:
            valid_dates.append(d_str)
            
    return valid_dates
