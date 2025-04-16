from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm, TipForm, PayCycleForm
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
def set_pay_cycle(request):
    cycle, created = PaycheckCycle.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        form = PayCycleForm(request.POST) # Form now only has start_date

        if form.is_valid():
            cycle.start_date = form.cleaned_data['start_date']
            # --- SET FREQUENCY AUTOMATICALLY ---
            cycle.frequency = PaycheckCycle.PayFrequency.BIWEEKLY # Use the choice value from model
            # --- --- --- --- --- --- --- --- ---
            cycle.save()

            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Pay cycle updated successfully!'})
            else:
                return redirect('user_tips')
        else:
            if is_ajax:
                # Errors will now only be for start_date if invalid
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            else:
                return redirect('user_tips') # Redirect back on error for non-AJAX

    # --- Handle GET requests ---
    # (No changes needed here, but ensure it works)
    is_ajax_get = request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if is_ajax_get:
         # Return current settings (frequency will be whatever is saved, likely 'biweekly')
         return JsonResponse({
             'start_date': cycle.start_date.strftime('%Y-%m-%d') if cycle.start_date else None,
             'frequency': cycle.frequency # Still useful to return if needed elsewhere
         })
    else:
        return redirect('user_tips')
    
@login_required
def user_tips(request, year=None, month=None):
    today = date.today()
    if not year or not month:
        year, month = today.year, today.month

    month = int(month)
    year = int(year)

    # --- Month Navigation Logic (remains the same) ---
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # --- Calendar Data Fetching (remains the same) ---
    first_day_month = date(year, month, 1)
    last_day_month = date(year, month, calendar.monthrange(year, month)[1])
    monthly_tips = Tip.objects.filter(user=request.user, date__date__range=[first_day_month, last_day_month]) # Use date__date for DateField comparison
    total_monthly_tip = monthly_tips.aggregate(Sum('amount'))['amount__sum'] or 0
    total_monthly_gratuity = monthly_tips.aggregate(Sum('gratuity'))['gratuity__sum'] or 0
    tip_dict = {tip.date.day: tip for tip in monthly_tips} # Assuming tip.date is DateTimeField

    # --- Calendar Grid Generation (remains the same) ---
    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    week = []
    for day in cal.itermonthdays(year, month):
        if day == 0:
            week.append(None)
        else:
            current_date_obj = date(year, month, day) # Create date object for comparison
            # Find tip matching the specific day (handle potential timezones if date is DateTimeField)
            tip_for_day = None
            for tip in monthly_tips:
                 # Compare only the date part
                 if tip.date.date() == current_date_obj:
                      tip_for_day = tip
                      break # Found the tip for this day
            week.append({'day': day, 'tip': tip_for_day, 'date': current_date_obj.strftime('%Y-%m-%d')}) # Add full date string

        if len(week) == 7:
            weeks.append(week)
            week = []
    if week:
        weeks.append(week)

    # --- Paycheck Calculation Logic (UPDATED) ---
    paycheck_cycle, created = PaycheckCycle.objects.get_or_create(user=request.user)
    paycheck_start_date = None
    paycheck_end_date = None
    paycheck_day = None # Estimated day user gets paid
    recent_total_tip = 0
    recent_total_gratuity = 0
    paycheck_total = 0

    if paycheck_cycle.start_date and paycheck_cycle.frequency:
        paycheck_start_date = paycheck_cycle.start_date
        # Calculate end date based on frequency
        if paycheck_cycle.frequency == PaycheckCycle.PayFrequency.WEEKLY:
            paycheck_end_date = paycheck_start_date + timedelta(days=6)
            paycheck_day = paycheck_end_date + timedelta(days=5) # Example: paid 5 days after cycle ends
        elif paycheck_cycle.frequency == PaycheckCycle.PayFrequency.BIWEEKLY:
            paycheck_end_date = paycheck_start_date + timedelta(days=13)
            paycheck_day = paycheck_end_date + timedelta(days=5) # Example: paid 5 days after cycle ends
        # Add logic for other frequencies if implemented

        if paycheck_end_date:
            # Ensure we filter tips within the calculated range
            # Use date__date if Tip.date is DateTimeField
            recent_tips = Tip.objects.filter(
                user=request.user,
                date__date__range=[paycheck_start_date, paycheck_end_date]
            )
            recent_total_tip = recent_tips.aggregate(Sum('amount'))['amount__sum'] or 0
            recent_total_gratuity = recent_tips.aggregate(Sum('gratuity'))['gratuity__sum'] or 0
            paycheck_total = recent_total_tip + recent_total_gratuity
    else:
        # Default behavior if cycle is not set (optional)
        # You could show a message asking the user to set their cycle
        pass


    # --- Pass paycheck_cycle to context ---
    context = {
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
        # Paycheck details
        "recent_total_tip": recent_total_tip,
        "recent_total_gratuity": recent_total_gratuity,
        "paycheck_total": paycheck_total,
        "paycheck_day": paycheck_day, # Can be None if not calculated
        "paycheck_cycle": paycheck_cycle, # Pass the object itself
    }
    return render(request, "myapp/user_tips.html", context)

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
