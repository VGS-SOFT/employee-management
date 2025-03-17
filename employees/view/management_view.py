from calendar import monthrange
from datetime import datetime, time, timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from ..models import (
    Holiday,
    Management,
    Modules,
    Notification,
    PersonalBreak,
    Projects,
    Status,
    Task,
    TeamRequest,
    TeamTask,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketPriority,
    User,
    Team,
    TimeRecord,
    WorkLog,
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


def get_status_display(status_code):
    """Helper function to get status display name"""
    for code, name in Ticket.TICKET_STATUS_CHOICES:
        if code == status_code:
            return name
    return status_code


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
    return render(request, "management/all_employees.html", context)


@login_required
def present_employees(request):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    today = timezone.now().date()
    attendance = (
        TimeRecord.objects.filter(check_in__date=today)
        .select_related("user", "user__team")
        .prefetch_related("breaks")  # Add this to get personal breaks
        .values(
            "id",  # Need this for breaks lookup
            "user__team__team_id",
            "user__email",
            "user__phone",
            "user__team__department",
            "check_in",
            "check_out",
        )
        .all()
    )

    # Calculate duration and get break information
    for record in attendance:
        # Get personal breaks for this record
        breaks = PersonalBreak.objects.filter(
            time_record_id=record["id"], check_out__date=today
        )

        total_break_time = timedelta()
        for break_record in breaks:
            if break_record.check_in:
                break_duration = break_record.check_in - break_record.check_out
                total_break_time += break_duration

        # Calculate total duration
        if record["check_out"]:
            total_duration = record["check_out"] - record["check_in"]
            working_duration = total_duration - total_break_time

            # Format durations
            hours = working_duration.seconds // 3600
            minutes = (working_duration.seconds % 3600) // 60
            record["working_duration"] = f"{hours:02d}:{minutes:02d}"

            hours = total_duration.seconds // 3600
            minutes = (total_duration.seconds % 3600) // 60
            record["total_duration"] = f"{hours:02d}:{minutes:02d}"
        else:
            record["working_duration"] = "-"
            record["total_duration"] = "-"

    context = {"data": attendance}
    return render(request, "management/present_employees.html", context)


@login_required
def employee_details(request, team_id):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    try:
        team = get_object_or_404(Team, team_id=team_id)
        employee = team.user

        # Get date range
        current_date = timezone.now()
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                start_date = current_date.replace(day=1).date()
                end_date = current_date.date()
        else:
            month_offset = int(request.GET.get("month_offset", 0))
            target_date = current_date - timedelta(days=month_offset * 30)
            start_date = target_date.replace(day=1).date()
            _, last_day = monthrange(target_date.year, target_date.month)
            end_date = target_date.replace(day=last_day).date()

        # Get holidays
        holidays = set(
            Holiday.objects.filter(
                date__range=[start_date, end_date], is_working_day=False
            ).values_list("date", flat=True)
        )

        # Calculate working days
        working_dates = []
        current = start_date
        while current <= end_date:
            # Skip Sundays and holidays
            if current.weekday() != 6 and current not in holidays:
                # For Saturdays, check if it's even week
                if current.weekday() == 5:
                    week_number = (current.day - 1) // 7 + 1
                    if week_number % 2 == 0:  # Even week Saturday
                        working_dates.append(current)
                else:
                    working_dates.append(current)  # Monday to Friday
            current += timedelta(days=1)

        total_working_days = len(working_dates)
        working_dates_set = set(working_dates)

        # Get attendance records
        attendance_records = []
        total_hours_missed = timedelta()
        present_dates = set()
        late_days = 0
        half_days = 0
        full_days = present_count = 0

        monthly_attendance = (
            TimeRecord.objects.filter(
                user=employee, check_in__date__range=[start_date, end_date]
            )
            .select_related("user")
            .prefetch_related("breaks")
        )

        for record in monthly_attendance:
            date = record.check_in.date()
            if date in working_dates_set:
                duration = timedelta()
                if record.check_out:
                    duration = record.check_out - record.check_in

                    # Subtract break durations
                    breaks = record.breaks.filter(check_in__isnull=False)
                    break_duration = sum(
                        (b.check_in - b.check_out).total_seconds() for b in breaks
                    )
                    duration = duration - timedelta(seconds=break_duration)

                    # Calculate attendance status
                    hours_worked = duration.total_seconds() / 3600
                    status = "Present"

                    if hours_worked < 3.5:
                        status = "Absent"
                    elif hours_worked < 6:
                        status = "Half Day"
                        half_days += 1
                    else:
                        full_days += 1
                        present_count += 1

                    if (
                        record.check_in.time()
                        > datetime.strptime("10:15", "%H:%M").time()
                    ):
                        late_days += 1

                    attendance_records.append(
                        {
                            "date": date,
                            "day": date.strftime("%A"),
                            "check_in": record.check_in.strftime("%I:%M %p"),
                            "check_out": record.check_out.strftime("%I:%M %p"),
                            "duration": f"{int(hours_worked):02d}:{int((hours_worked % 1) * 60):02d}",
                            "status": status,
                            "is_late": record.check_in.time()
                            > datetime.strptime("10:15", "%H:%M").time(),
                        }
                    )
                else:
                    # Handle case where check_out is None (still checked in)
                    attendance_records.append(
                        {
                            "date": date,
                            "day": date.strftime("%A"),
                            "check_in": record.check_in.strftime("%I:%M %p"),
                            "check_out": "-",
                            "duration": "In Progress",
                            "status": "Present",
                            "is_late": record.check_in.time()
                            > datetime.strptime("10:15", "%H:%M").time(),
                        }
                    )
                present_dates.add(date)

        # Calculate absent dates (exclude future dates)
        today = timezone.now().date()
        absent_dates = [
            {"date": date, "day": date.strftime("%A"), "reason": "No attendance record"}
            for date in working_dates_set - present_dates
            if date <= today  # Only include dates up to today
        ]

        # Recalculate attendance summary excluding future dates
        total_working_days = len([date for date in working_dates if date <= today])

        # Calculate weekend dates
        weekend_dates = {"sundays": [], "saturdays": []}

        current = start_date
        while current <= end_date:
            if current.weekday() == 6:  # Sunday
                weekend_dates["sundays"].append(current)
            elif current.weekday() == 5:  # Saturday
                week_number = (current.day - 1) // 7 + 1
                weekend_dates["saturdays"].append(
                    {
                        "date": current,
                        "is_working": week_number % 2
                        == 0,  # Even week Saturdays are working
                    }
                )
            current += timedelta(days=1)

        context = {
            "employee": employee,
            "team_details": {"team_id": team.team_id, "department": team.department},
            "attendance_summary": {
                "total_working_days": total_working_days,
                "present_days": present_count,
                "absent_days": len(absent_dates),
                "half_days": half_days,
                "late_days": late_days,
                "attendance_percentage": (
                    round((present_count / total_working_days * 100), 2)
                    if total_working_days > 0
                    else 0
                ),
            },
            "attendance_records": attendance_records,
            "absent_dates": sorted(absent_dates, key=lambda x: x["date"]),
            "date_range": {
                "start": start_date,
                "end": end_date,
                "current_period": f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
            },
            "weekend_dates": weekend_dates,
        }

        return render(request, "management/employee_details.html", context)

    except Exception as e:
        messages.error(request, f"Error loading employee details: {str(e)}")
        return redirect("all_employees")


# Project Data
@login_required
def all_projects(request):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can view projects.")
        return redirect("dashboard")

    projects = Projects.objects.all()
    return render(request, "management/all_projects.html", {"data": projects})


@login_required
def add_project(request):
    # Check if user is management
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can create projects.")
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status_id = request.POST.get("status")

        if not name:
            messages.error(request, "Project name is required.")
            return redirect("all_projects")

        try:
            status = Status.objects.get(id=status_id)
            management_user = User.objects.get(email=request.user.email)
            management = Management.objects.get(user=management_user)

            Projects.objects.create(
                name=name,
                description=description,
                status=status,
                created_by=management,
            )
            messages.success(request, "Project created successfully!")
            return redirect("all_projects")

        except Status.DoesNotExist:
            messages.error(request, "Invalid status selected.")
            return redirect("add_project")
        except Exception as e:
            messages.error(request, f"Error creating project: {str(e)}")
            return redirect("add_project")

    # For GET request
    statuses = Status.objects.filter(is_active=True)
    context = {"statuses": statuses}
    return render(request, "management/add_project.html", context)


@login_required
def delete_project(request, id: int):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Only management users can delete projects.")
        return redirect("login")

    try:
        project = get_object_or_404(Projects, id=id)
        project.delete()
        messages.success(request, "Project deleted successfully")
    except Exception as e:
        print(f"Error while deleting the project: {e}")
        messages.error(request, "An error occurred while deleting the project.")

    return redirect("all_projects")


# Modules Data
@login_required
def all_modules(request):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Only management users can delete projects.")
        return redirect("login")

    try:
        data = Modules.objects.filter(is_active=True)
        context = {"data": data}
        return render(request, "management/all_modules.html", context)
    except Exception as es:
        print(
            f"Error while fetching the data from all_modules: {str(es)}"
        )  # Better readability
        messages.error(
            request, f"An error occurred: {es}"
        )  # Show error message to user
        return redirect("all_projects")


@login_required
def delete_module(request, id: int):
    if request.user.role != "MANAGEMENT":
        logout(request)
        messages.error(request, "Only management users can delete modules.")
        return redirect("login")

    try:
        module = get_object_or_404(Modules, id=id)
        module.delete()
        messages.success(request, "module deleted successfully")
    except Exception as e:
        print(f"Error while deleting the module: {e}")
        messages.error(request, "An error occurred while deleting the module.")

    return redirect("all_modules")


@login_required
def add_module(request):
    # Check if user is management
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Only management users can create modules.")
        return redirect("dashboard")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        status_id = request.POST.get("status")
        project_id = request.POST.get("project")

        if not name:
            messages.error(request, "module name is required.")
            return redirect("all_modules")

        try:
            status = Status.objects.get(id=status_id)
            project = Projects.objects.get(id=project_id)
            management_user = User.objects.get(email=request.user.email)
            management = Management.objects.get(user=management_user)

            Modules.objects.create(
                name=name,
                description=description,
                status=status,
                project=project,
                created_by=management,
            )
            messages.success(request, "module created successfully!")
            return redirect("all_modules")

        except Status.DoesNotExist:
            messages.error(request, "Invalid status selected.")
            return redirect("add_module")
        except Exception as e:
            messages.error(request, f"Error creating module: {str(e)}")
            return redirect("add_module")

    # For GET request
    statuses = Status.objects.filter(is_active=True)
    projects = Projects.objects.filter(is_active=True)
    context = {"statuses": statuses, "projects": projects}
    return render(request, "management/add_module.html", context)


# Tasks
@login_required
def admin_task_details(request, task_id):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    try:
        task = get_object_or_404(
            TeamTask.objects.select_related(
                "project",
                "module",
                "status",
                "manager",
                "created_by",
                "created_by__user",  # This gets the user details of the team member
            ),
            id=task_id,
        )

        context = {
            "task": task,
        }
        return render(request, "management/team_task_details.html", context)
    except Exception as e:
        messages.error(request, f"Error loading task details: {str(e)}")
        return redirect("all_tasks")


@login_required
def management_view_all_tasks(request):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    try:
        # Get all tasks including both Team tasks and regular tasks
        team_tasks = TeamTask.objects.select_related(
            "project", "module", "status", "manager", "created_by", "created_by__user"
        ).filter(is_active=True)

        regular_tasks = (
            Task.objects.select_related(
                "project", "module", "status", "created_by", "assigned_by"
            )
            .prefetch_related("assigned_to")
            .filter(is_active=True)
        )

        context = {
            "team_tasks": team_tasks,
            "regular_tasks": regular_tasks,
        }
        return render(request, "management/all_tasks.html", context)
    except Exception as e:
        messages.error(request, f"Error loading tasks: {str(e)}")
        return redirect("management_dashboard")


# Worklog
@login_required
def management_view_all_worklogs(request):
    if request.user.role != "MANAGEMENT":
        messages.error(request, "Access denied. Management privileges required.")
        return redirect("login")

    try:
        # Get base queryset with all necessary related fields
        work_logs = WorkLog.objects.select_related(
            "team_member",
            "team_member__user",
            "task",
            "task__project",
            "task__module",
            "status",
        ).order_by("-created_at")

        # Get unique team members for filtering
        team_members = (
            Team.objects.select_related("user")
            .filter(id__in=work_logs.values_list("team_member_id", flat=True))
            .distinct()
        )

        context = {
            "work_logs": work_logs,
            "team_members": team_members,
        }
        return render(request, "management/view_all_worklogs.html", context)

    except Exception as e:
        messages.error(request, f"Error loading work logs: {str(e)}")
        return redirect("management_dashboard")


# Tickets
@login_required
def management_tickets(request):
    """
    View for management to see and manage all tickets in the system
    """
    try:
        # Get management profile
        management = Management.objects.get(user=request.user)

        # Get filter parameters
        status_filter = request.GET.get("status", "")
        priority_filter = request.GET.get("priority", "")
        category_filter = request.GET.get("category", "")
        assigned_filter = request.GET.get("assigned", "")

        # Base queryset
        tickets = Ticket.objects.all().order_by("-created_at")

        # Apply filters
        if status_filter:
            tickets = tickets.filter(status=status_filter)

        if priority_filter:
            tickets = tickets.filter(priority_id=priority_filter)

        if category_filter:
            tickets = tickets.filter(category_id=category_filter)

        if assigned_filter:
            if assigned_filter == "me":
                tickets = tickets.filter(assigned_to=management)
            elif assigned_filter == "unassigned":
                tickets = tickets.filter(assigned_to__isnull=True)

        # Get all available filters for dropdowns
        status_choices = Ticket.TICKET_STATUS_CHOICES
        priorities = TicketPriority.objects.all().order_by("order")
        categories = TicketCategory.objects.filter(is_active=True)

        # Get ticket stats
        stats = {
            "total": Ticket.objects.count(),
            "new": Ticket.objects.filter(status="NEW").count(),
            "in_progress": Ticket.objects.filter(status="IN_PROGRESS").count(),
            "on_hold": Ticket.objects.filter(status="ON_HOLD").count(),
            "resolved": Ticket.objects.filter(status="RESOLVED").count(),
            "closed": Ticket.objects.filter(status="CLOSED").count(),
            "assigned_to_me": Ticket.objects.filter(assigned_to=management).count(),
            "unassigned": Ticket.objects.filter(assigned_to__isnull=True).count(),
        }

        # Pagination
        paginator = Paginator(tickets, 15)  # Show 15 tickets per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "tickets": page_obj,
            "status_choices": status_choices,
            "priorities": priorities,
            "categories": categories,
            "current_filters": {
                "status": status_filter,
                "priority": priority_filter,
                "category": category_filter,
                "assigned": assigned_filter,
            },
            "stats": stats,
            "management": management,
        }

        return render(request, "management/tickets_dashboard.html", context)

    except Management.DoesNotExist:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("team_dashboard")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("management_dashboard")


@login_required
def management_ticket_detail(request, ticket_id):
    """
    View for management to see and manage a specific ticket
    """
    try:
        # Get management profile
        management = Management.objects.get(user=request.user)

        # Get ticket with related objects
        ticket = get_object_or_404(Ticket, id=ticket_id)
        comments = TicketComment.objects.filter(ticket=ticket).order_by("created_at")
        attachments = TicketAttachment.objects.filter(ticket=ticket)

        # Get all managers for assignment dropdown
        managers = Management.objects.all()

        # Process form submissions
        if request.method == "POST":
            action = request.POST.get("action", "")

            # Handle status update
            if action == "update_status":
                new_status = request.POST.get("status")
                old_status = ticket.status

                ticket.status = new_status

                # If resolved or closed, add resolution timestamp
                if new_status in ["RESOLVED", "CLOSED"] and old_status not in [
                    "RESOLVED",
                    "CLOSED",
                ]:
                    ticket.resolved_at = timezone.now()

                    # Add resolution notes if provided
                    resolution_notes = request.POST.get("resolution_notes", "")
                    if resolution_notes:
                        ticket.resolution_notes = resolution_notes

                ticket.save()

                # Add a system comment about the status change
                TicketComment.objects.create(
                    ticket=ticket,
                    user=request.user,
                    comment=f"Status changed from {get_status_display(old_status)} to {get_status_display(new_status)}",
                    is_private=True,
                )

                messages.success(
                    request,
                    f"Ticket status updated to {get_status_display(new_status)}",
                )

            # Handle assignment update
            elif action == "update_assignment":
                assigned_to_id = request.POST.get("assigned_to", "")
                old_assignee = ticket.assigned_to

                if assigned_to_id:
                    new_assignee = get_object_or_404(Management, id=assigned_to_id)
                    ticket.assigned_to = new_assignee

                    if not old_assignee:
                        ticket.status = "ASSIGNED"
                else:
                    ticket.assigned_to = None

                ticket.save()

                # Add a system comment about the assignment change
                if old_assignee != ticket.assigned_to:
                    old_name = old_assignee.user.name if old_assignee else "Unassigned"
                    new_name = (
                        ticket.assigned_to.user.name
                        if ticket.assigned_to
                        else "Unassigned"
                    )

                    TicketComment.objects.create(
                        ticket=ticket,
                        user=request.user,
                        comment=f"Ticket assignment changed from {old_name} to {new_name}",
                        is_private=True,
                    )

                messages.success(request, "Ticket assignment updated")

            # Handle adding a comment
            elif action == "add_comment":
                comment_text = request.POST.get("comment", "").strip()
                is_private = request.POST.get("is_private", "") == "on"

                if comment_text:
                    TicketComment.objects.create(
                        ticket=ticket,
                        user=request.user,
                        comment=comment_text,
                        is_private=is_private,
                    )
                    messages.success(request, "Comment added successfully")
                else:
                    messages.error(request, "Comment cannot be empty")

                # Refresh the ticket and related objects
                ticket = get_object_or_404(Ticket, id=ticket_id)
                comments = TicketComment.objects.filter(ticket=ticket).order_by(
                    "created_at"
                )

            return redirect("management_ticket_detail", ticket_id=ticket.id)

        context = {
            "ticket": ticket,
            "comments": comments,
            "attachments": attachments,
            "managers": managers,
            "status_choices": Ticket.TICKET_STATUS_CHOICES,
            "is_management": True,
            "management": management,
        }

        return render(request, "management/ticket_detail.html", context)

    except Management.DoesNotExist:
        messages.error(request, "You don't have permission to access this page.")
        return redirect("team_dashboard")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("management_tickets")


# Team Requests
@login_required
def management_all_requests(request):
    """View for management to see all team requests"""
    # Ensure user is management or admin
    if request.user.role not in ["MANAGEMENT", "ADMIN"]:
        messages.error(request, "You don't have permission to access this page")
        return redirect("team_dashboard")

    # Get all requests
    all_requests = TeamRequest.objects.all().order_by("-created_at")

    return render(
        request,
        "management/management_all_requests.html",
        {
            "all_requests": all_requests,
        },
    )


@login_required
def management_process_request(request, request_id):
    """View for management to process (approve/reject) a team request"""
    # Ensure user is management or admin
    if request.user.role not in ["MANAGEMENT", "ADMIN"]:
        messages.error(request, "You don't have permission to access this page")
        return redirect("team_dashboard")

    try:
        team_request = TeamRequest.objects.get(pk=request_id)
    except TeamRequest.DoesNotExist:
        messages.error(request, "Request not found")
        return redirect("management_all_requests")

    if request.method == "POST":
        status = request.POST.get("status")
        review_notes = request.POST.get("review_notes")

        if status not in ["APPROVED", "REJECTED"]:
            messages.error(request, "Invalid status")
            return redirect("management_process_request", request_id=request_id)

        # Update request
        team_request.status = status
        team_request.review_notes = review_notes
        team_request.reviewed_by = request.user
        team_request.reviewed_at = timezone.now()
        team_request.save()

        # If approved and it's a check-in/out request, create or update TimeRecord
        if status == "APPROVED":
            user = team_request.user
            date = team_request.date

            # Get or create TimeRecord for the date
            time_record = None

            # For check-in
            if team_request.check_in and team_request.check_in_time:
                # Combine date and time to create datetime
                check_in_datetime = timezone.make_aware(
                    datetime.combine(date, team_request.check_in_time)
                )

                # Try to find existing record for that day
                try:
                    time_record = TimeRecord.objects.get(user=user, check_in__date=date)
                    # Update existing check-in
                    time_record.check_in = check_in_datetime
                except TimeRecord.DoesNotExist:
                    # Create new record
                    time_record = TimeRecord(user=user, check_in=check_in_datetime)

                time_record.save()

            # For check-out
            if team_request.check_out and team_request.check_out_time:
                # If we haven't loaded the record yet and there's a check-out
                if not time_record:
                    try:
                        time_record = TimeRecord.objects.get(
                            user=user, check_in__date=date
                        )
                    except TimeRecord.DoesNotExist:
                        # This is unusual - check-out without check-in
                        messages.warning(
                            request,
                            f"Approved check-out for {user.name} on {date}, but no check-in record exists.",
                        )
                        # We'll create a new record with check-in at midnight
                        check_in_midnight = timezone.make_aware(
                            datetime.combine(date, time(0, 0))
                        )
                        time_record = TimeRecord(user=user, check_in=check_in_midnight)

                if time_record:
                    # Combine date and time for check-out
                    check_out_datetime = timezone.make_aware(
                        datetime.combine(date, team_request.check_out_time)
                    )
                    time_record.check_out = check_out_datetime
                    time_record.save()

        # Notify the team member
        Notification.objects.create(
            recipient=team_request.user,
            type="SYSTEM",
            title=f"Request {status.lower()}",
            message=f"Your request for {team_request.date} has been {status.lower()}"
            + (f": {review_notes}" if review_notes else ""),
        )

        messages.success(request, f"Request has been {status.lower()}")
        return redirect("management_all_requests")

    return render(
        request,
        "management/process_request.html",
        {
            "team_request": team_request,
        },
    )
