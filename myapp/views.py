from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm, TipForm, PaycheckCycleForm
from .models import Tip, PaycheckCycle
from django.contrib.auth.decorators import login_required
import calendar
from datetime import date, timedelta, datetime
from django.db.models import Sum
from django.http import JsonResponse
from django.forms.models import model_to_dict

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
    # Handle GET request (for direct access or non-JS fallback)
    if request.method == 'GET':
        # Pre-fill date from query parameter if provided (for modal or direct link)
        initial_data = {}
        date_str = request.GET.get('date')
        if date_str:
            try:
                initial_data['date'] = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass # Ignore invalid date format
        
        form = TipForm(initial=initial_data)
        # Render the full page template if accessed directly via GET
        return render(request, 'myapp/add_tip_form.html', {'form': form}) # Or wherever your full form page is

    # Handle POST request (from modal AJAX or direct form submission)
    elif request.method == 'POST':
        form = TipForm(request.POST)
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if form.is_valid():
            tip = form.save(commit=False)
            tip.user = request.user # Associate tip with logged-in user
            tip.save()
            
            if is_ajax:
                # Return JSON success response for AJAX
                return JsonResponse({'status': 'success', 'message': 'Tip added successfully!'})
            else:
                # Redirect for traditional form submission
                # Redirect back to the calendar view for the month the tip was added to
                tip_date = form.cleaned_data.get('date')
                if tip_date:
                    return redirect('user_tips', year=tip_date.year, month=tip_date.month)
                else:
                    return redirect('user_tips_current') # Or some default view

        else: # Form is invalid
            if is_ajax:
                # Return JSON error response with form errors for AJAX
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400) # Use 400 status code
            else:
                # Re-render the full form page with errors for traditional submission
                # You might need to pass the original date back if needed
                return render(request, 'myapp/add_tip_form.html', {'form': form}) 

    # Handle other methods if necessary (optional)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def edit_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id, user=request.user)  # Ensure the user owns this tip
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == "GET":
        if is_ajax:
            # For AJAX GET, return tip data as JSON
            # Use model_to_dict but be careful about sensitive fields if any
            # Convert Decimal to string for JSON compatibility
            tip_data = model_to_dict(tip, fields=['id', 'amount', 'gratuity', 'date', 'note'])
            tip_data['amount'] = str(tip_data['amount']) # Convert Decimal
            tip_data['gratuity'] = str(tip_data['gratuity']) # Convert Decimal
            # Format date/datetime as needed by the frontend input (YYYY-MM-DD)
            if isinstance(tip_data['date'], datetime):
                 tip_data['date'] = tip_data['date'].strftime('%Y-%m-%dT%H:%M:%S') # ISO format often useful
            elif isinstance(tip_data['date'], date):
                 tip_data['date'] = tip_data['date'].strftime('%Y-%m-%d')

            return JsonResponse({'tip': tip_data})
        else:
            # For standard GET, render the edit form page
            form = TipForm(instance=tip)
            return render(request, 'myapp/edit_tip.html', {'form': form, 'tip': tip})

    elif request.method == "POST":
        form = TipForm(request.POST, instance=tip)
        if form.is_valid():
            form.save()
            if is_ajax:
                # For AJAX POST success, return JSON
                return JsonResponse({'status': 'success', 'message': 'Tip updated successfully!'})
            else:
                # For standard POST success, redirect
                tip_date = form.cleaned_data.get('date')
                if tip_date:
                    return redirect('user_tips', year=tip_date.year, month=tip_date.month)
                else:
                    # Find the month/year from the original tip instance if form date isn't reliable
                    return redirect('user_tips', year=tip.date.year, month=tip.date.month) 
        else: # Form is invalid
            if is_ajax:
                # For AJAX POST error, return JSON with errors
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            else:
                # For standard POST error, re-render the edit form page
                return render(request, 'myapp/edit_tip.html', {'form': form, 'tip': tip})

    # Handle other methods if necessary
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def delete_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id, user=request.user)
    
    # It's generally safer to require POST for delete operations
    if request.method == "POST": 
        tip_year = tip.date.year
        tip_month = tip.date.month
        tip.delete()
        # Add AJAX handling here if needed later
        # For now, redirect back to the month the tip was in
        return redirect('user_tips', year=tip_year, month=tip_month) 
    
    # If GET, show a confirmation page (good practice)
    # Make sure you have a 'confirm_delete.html' template
    return render(request, 'myapp/confirm_delete.html', {'tip': tip}) 
