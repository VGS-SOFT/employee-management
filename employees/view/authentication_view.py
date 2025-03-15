from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required


@never_cache
def login_view(request):
    """Handle user authentication and login"""
    # Redirect if user is already logged in
    if request.user.is_authenticated:
        if request.user.role == "ADMIN":
            return redirect("/admin/")
        elif request.user.role == "MANAGEMENT":
            return redirect("management_dashboard")
        else:  # TEAM role
            return redirect("team_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Set cookie if remember me is checked
            response = redirect(
                "management_dashboard"
                if user.role == "MANAGEMENT"
                else "team_dashboard"
            )
            if remember_me:
                response.set_cookie(
                    "remembered_username", username, max_age=30 * 24 * 60 * 60
                )  # 30 days
            else:
                response.delete_cookie("remembered_username")

            return response
        else:
            messages.error(request, "Invalid username or password")
            return redirect("login")

    # Get remembered username from cookie
    remembered_username = request.COOKIES.get("remembered_username", "")
    return render(
        request,
        "authentication/login.html",
        {"remembered_username": remembered_username},
    )


@login_required
def logout_view(request):
    """Handle user logout"""
    # Only remove the session, keep the remember_me cookie if it exists
    logout(request)
    messages.success(request, "You have been successfully logged out")
    return redirect("login")
