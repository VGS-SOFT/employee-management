from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from ..models import (
    User,
    Team,
    TimeRecord,
    WorkSchedule,
)

# Helper function to calculate the late arrivial.
def calculate_late_arrivals(attendance_queryset):
    """Calculate late arrivals based on work schedules"""
    late_arrivals = 0
    for record in attendance_queryset:
        schedule = (
            record.user.work_schedules.first()
            or WorkSchedule.objects.filter(is_default=True).first()
        )
        if schedule and record.check_in.time() > schedule.start_time:
            late_arrivals += 1
    return late_arrivals


# Management View Data.
@login_required
def dashboard(request):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    today = timezone.now().date()

    # Get all team members
    team_members = User.objects.filter(role="TEAM", is_active=True)
    total_employees = team_members.count()

    # Get today's attendance
    attendance = TimeRecord.objects.filter(check_in__date=today).select_related("user")
    present_today = attendance.values("user").distinct().count()
    late_arrivals = calculate_late_arrivals(attendance)

    # Calculate attendance percentage
    attendance_percentage = (
        round((present_today / total_employees * 100), 1) if total_employees > 0 else 0
    )
    late_percentage = (
        round((late_arrivals / present_today * 100), 1) if present_today > 0 else 0
    )

    # Get recent activities
    recent_activities = []

    # Add check-ins
    recent_checkins = TimeRecord.objects.filter(check_in__date=today).select_related(
        "user"
    )[:5]

    for checkin in recent_checkins:
        recent_activities.append(
            {
                "title": checkin.user.name,
                "description": f"Arrived at {checkin.check_in.strftime('%I:%M %p')}",
                "timestamp": checkin.check_in,
            }
        )

    context = {
        "total_employees": total_employees,
        "present_today": present_today,
        "late_arrivals": late_arrivals,
        "new_employees_count": Team.objects.filter(user__role="TEAM").count(),
        "attendance_percentage": attendance_percentage,
        "late_percentage": late_percentage,
        "recent_activities": sorted(
            recent_activities, key=lambda x: x["timestamp"], reverse=True
        )[:10],
    }

    return render(request, "management/dashboard.html", context)


@login_required
def all_employees(request):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    # Get active users first
    active_users = User.objects.filter(is_active=True, role="TEAM").values_list(
        "id", flat=True
    )

    # Then get team members whose users are active
    team_members = (
        Team.objects.filter(user_id__in=active_users)
        .select_related("user")
        .values(
            "team_id",
            "department",
            "user__email",  # Get email from User model
            "user__phone",  # Get phone from User model
        )
        .all()
    )

    context = {"data": team_members}
    return render(request, "admins/all_employees.html", context)
    