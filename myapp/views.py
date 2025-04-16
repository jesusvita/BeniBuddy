from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm, TipForm, PaycheckCycleForm
from .models import Tip, PaycheckCycle
from django.contrib.auth.decorators import login_required
import calendar
from datetime import date, timedelta, datetime
from django.db.models import Sum

def home(request):
    if request.user.is_authenticated:
        return redirect('user_tips')  # If logged in, go to tips page
    return render(request, 'myapp/home.html')  # Show login screen

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new user
            return redirect('login')  # Redirect to login page after successful registration
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})

@login_required
def set_paycheck_cycle(request):
    cycle, created = PaycheckCycle.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = PaycheckCycleForm(request.POST, instance=cycle)
        if form.is_valid():
            form.save()
            return redirect('user_tips')  # or wherever you want
    else:
        form = PaycheckCycleForm(instance=cycle)

    return render(request, 'myapp/set_cycle.html', {'form': form})

@login_required
def user_tips(request, year=None, month=None):
    # Get the current year and month if not provided
    today = date.today()
    start_date = today - timedelta(days=14)

    if not year or not month:
        year, month = today.year, today.month

    # Ensure month stays within range (1-12)
    month = int(month)
    year = int(year)

    # Handle Previous and Next Month Navigation
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # Get first and last day of the month
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # Get all tips for the user within the month
    tips = Tip.objects.filter(user=request.user, date__range=[first_day, last_day])

    # Add all tips for the user within the month 
    total_monthly_tip = tips.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Add all gratuity for the user within the month
    total_monthly_gratuity = tips.aggregate(Sum('gratuity'))['gratuity__sum'] or 0

    # Organize tips into a dictionary {day: tip}
    tip_dict = {tip.date.day: tip for tip in tips}

    # Generate calendar grid
    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    week = []

    for day in cal.itermonthdays(year, month):
        if day == 0:
            week.append(None)  # Empty day for padding
        else:
            week.append({'day': day, 'tip': tip_dict.get(day)})  # Store tip data

        if len(week) == 7:  # End of the week
            weeks.append(week)
            week = []

    if week:  # Add the last incomplete week
        weeks.append(week)

    try:
        cycle = PaycheckCycle.objects.get(user=request.user)
        start_date = cycle.start_date
        end_date = start_date + timedelta(days=13)  # 2-week window
    except PaycheckCycle.DoesNotExist:
        start_date = today - timedelta(days=14)
        end_date = today
    
    recent_tips = Tip.objects.filter(user=request.user, date__range=[start_date, end_date])

    total_tip = recent_tips.aggregate(Sum('amount'))['amount__sum'] or 0
    total_gratuity = recent_tips.aggregate(Sum('gratuity'))['gratuity__sum'] or 0
    paycheck_total = total_tip + total_gratuity
    paycheck_day = end_date + timedelta(days=5)
    return render(request, "myapp/user_tips.html", {
        "weeks": weeks,
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "total_monthly_tip": total_monthly_tip,
        "total_monthly_gratuity": total_monthly_gratuity,
        "recent_total_tip": total_tip,
        "recent_total_gratuity": total_gratuity,
        "paycheck_total": paycheck_total,
        "paycheck_day": paycheck_day,
    })
@login_required
def add_tip(request):
    # Get date from query string
    date_str = request.GET.get('date')
    initial_data = {}
    
    if date_str:
        try:
            initial_data['date'] = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass  # fallback to blank if format is off

    if request.method == "POST":
        form = TipForm(request.POST)
        if form.is_valid():
            tip = form.save(commit=False)
            tip.user = request.user
            tip.date = initial_data['date']
            tip.save()
            return redirect('user_tips')
    else:
        form = TipForm(initial=initial_data)

    return render(request, "myapp/add_tip.html", {"form": form})

@login_required
def edit_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id, user=request.user)  # Ensure the user owns this tip
    
    if request.method == "POST":
        form = TipForm(request.POST, instance=tip)
        if form.is_valid():
            form.save()
            return redirect('user_tips')  # Redirect back to tips page after editing
    else:
        form = TipForm(instance=tip)  # Pre-fill the form with existing tip data

    return render(request, 'myapp/edit_tip.html', {'form': form, 'tip': tip})

@login_required
def delete_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id, user=request.user)  # Ensure the user owns this tip
    
    if request.method == "POST":
        tip.delete()
        return redirect('user_tips')  # Redirect back to the tips page after deletion
    
    return render(request, 'myapp/confirm_delete.html', {'tip': tip})

def delete_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id, user=request.user)
    tip.delete()
    return redirect('user_tips')  # or your calendar view name