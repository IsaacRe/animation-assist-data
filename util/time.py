from datetime import datetime, timedelta


def get_upload_time_upper_bound() -> int:
    # subtract one day to avoid timezone discrepancies
    return int((datetime.utcnow() - timedelta(days=1)).timestamp())
