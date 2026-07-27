from .models import BacktestRun


def latest_completed_run_for(user):
    """Return a user's newest completed run that has a saved result."""
    return (
        BacktestRun.objects.filter(
            user=user,
            status="completed",
            completed_at__isnull=False,
            result__isnull=False,
        )
        .select_related("strategy", "result")
        .order_by("-completed_at", "-id")
        .first()
    )
