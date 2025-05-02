from django.shortcuts import render, redirect, get_object_or_404
from .forms import SignUpForm, TipForm, PayCycleForm
from .models import Tip, PaycheckCycle
from django.contrib.auth.decorators import login_required
import calendar
from datetime import date, timedelta, datetime
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.forms.models import model_to_dict
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import models
import decimal

def home(request):
    if request.user.is_authenticated:
        return redirect('user_tips')  # If logged in, go to tips page
    return redirect('login')  # Show login screen

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
@require_http_methods(["GET", "POST"]) # Only allow GET/POST for setting cycle
def set_pay_cycle(request):
    cycle, created = PaycheckCycle.objects.get_or_create(user=request.user)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
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
                # Should ideally not happen if triggered from modal, but good fallback
                return redirect('user_tips')
        else: # Form invalid
            if is_ajax:
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            else:
                 # Re-render the page with errors? Or just redirect? Redirect is simpler for now.
                return redirect('user_tips')

    # --- Handle GET requests (Primarily for AJAX fetching current settings) ---
    elif request.method == 'GET':
        if is_ajax:
            # Return current settings
            return JsonResponse({
                'start_date': cycle.start_date.strftime('%Y-%m-%d') if cycle.start_date else None,
                'frequency': cycle.frequency
            })
        else:
            # Non-AJAX GET doesn't make sense here, redirect to main page
            return redirect('user_tips')

@login_required
def user_tips(request, year=None, month=None):
    # Use timezone-aware date if timezones are enabled in settings.py
    # today_date = timezone.localdate()
    today_date = date.today() # Use this if timezones are not critical/enabled

    current_year, current_month = today_date.year, today_date.month

    # Use provided year/month or default to current
    year = int(year) if year else current_year
    month = int(month) if month else current_month

    # Validate month/year
    if not (1 <= month <= 12):
        month = current_month

    # --- Month Navigation Logic ---
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # --- Calendar Data Fetching ---
    try:
        first_day_month = date(year, month, 1)
        last_day_val = calendar.monthrange(year, month)[1]
        last_day_month = date(year, month, last_day_val)
    except ValueError:
        return redirect('user_tips')

    # Fetch tips for the displayed calendar month
    monthly_tips = Tip.objects.filter(
        user=request.user,
        date__date__range=[first_day_month, last_day_month]
    ).order_by('date')

    # Calculate totals for the displayed month - CORRECTED AGGREGATION
    monthly_aggregation = monthly_tips.aggregate(
        total_tip=Coalesce(Sum('amount'), decimal.Decimal('0.00'), output_field=DecimalField()),
        total_gratuity=Coalesce(Sum('gratuity'), decimal.Decimal('0.00'), output_field=DecimalField()),
        total_cash=Coalesce(Sum('cash_made'), decimal.Decimal('0.00'), output_field=DecimalField()), # Add cash
        total_hours=Coalesce(Sum('hours_worked'), decimal.Decimal('0.00'), output_field=DecimalField()) # Add hours
    )
    total_monthly_tip = monthly_aggregation['total_tip']
    total_monthly_gratuity = monthly_aggregation['total_gratuity']
    total_monthly_cash = monthly_aggregation['total_cash'] 
    total_monthly_hours = monthly_aggregation['total_hours']

    # Create a dictionary for quick lookup in calendar generation
    tip_dict = {tip.date.date(): tip for tip in monthly_tips}

    # --- Calendar Grid Generation ---
    cal = calendar.Calendar(firstweekday=6) # Sunday as first day
    weeks = []
    for week_days in cal.monthdatescalendar(year, month):
        week_data = []
        for day_date in week_days:
            if day_date.month == month:
                tip_for_day = tip_dict.get(day_date)
                week_data.append({
                    'day': day_date.day,
                    'tip': tip_for_day,
                    'date': day_date.strftime('%Y-%m-%d')
                })
            else:
                week_data.append(None)
        weeks.append(week_data)


    # --- Paycheck Calculation Logic (Based ONLY on Anchor Date) ---
    paycheck_cycle, created = PaycheckCycle.objects.get_or_create(user=request.user)
    paycheck_anchor_date = None # The user's configured start date
    target_cycle_start_date = None # Start date of the cycle beginning on the anchor date
    target_cycle_end_date = None   # End date of the cycle beginning on the anchor date
    paycheck_day_display = None    # The end date to display in the template
    recent_total_tip = 0.0
    recent_total_gratuity = 0.0
    recent_total_cash = decimal.Decimal('0.00') # Add cash
    recent_total_hours = decimal.Decimal('0.00') # Add hours
    paycheck_total = 0.0

    if paycheck_cycle.start_date and paycheck_cycle.frequency:
        paycheck_anchor_date = paycheck_cycle.start_date
        cycle_length = 14 if paycheck_cycle.frequency == PaycheckCycle.PayFrequency.BIWEEKLY else (7 if paycheck_cycle.frequency == PaycheckCycle.PayFrequency.WEEKLY else 0)

        if cycle_length > 0:
            target_cycle_start_date = paycheck_anchor_date
            target_cycle_end_date = target_cycle_start_date + timedelta(days=cycle_length - 1)
            paycheck_day_display = target_cycle_end_date + timedelta(days=5) # Assuming 5 days after cycle end

            recent_tips = Tip.objects.filter(
                user=request.user,
                date__date__range=[target_cycle_start_date, target_cycle_end_date]
            )

            # --- Updated Aggregation for paycheck cycle ---
            cycle_aggregation = recent_tips.aggregate(
                total_tip=Coalesce(Sum('amount'), decimal.Decimal('0.00'), output_field=DecimalField()),
                total_gratuity=Coalesce(Sum('gratuity'), decimal.Decimal('0.00'), output_field=DecimalField()),
                total_cash=Coalesce(Sum('cash_made'), decimal.Decimal('0.00'), output_field=DecimalField()), # Add cash
                total_hours=Coalesce(Sum('hours_worked'), decimal.Decimal('0.00'), output_field=DecimalField()) # Add hours
            )
            recent_total_tip = cycle_aggregation['total_tip']
            recent_total_gratuity = cycle_aggregation['total_gratuity']
            recent_total_cash = cycle_aggregation['total_cash']
            recent_total_hours = cycle_aggregation['total_hours']
            paycheck_total = recent_total_tip + recent_total_gratuity



    # --- Context ---
    # Make sure to update the context key name if you changed the variable name
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
        "recent_total_tip": recent_total_tip,
        "recent_total_gratuity": recent_total_gratuity,
        "paycheck_total": paycheck_total,
        "paycheck_day": paycheck_day_display, # Use the new variable name for clarity
        "paycheck_cycle": paycheck_cycle,
        "total_monthly_cash": total_monthly_cash,
        "recent_total_hours": recent_total_hours,
        
        
    }
    return render(request, "myapp/user_tips.html", context)

@login_required
@require_http_methods(["GET", "POST"]) # Allow GET for form display, POST for submission
def add_tip(request):
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = TipForm(request.POST)
        if form.is_valid():
            tip = form.save(commit=False)
            tip.user = request.user

            # Ensure date is stored correctly (handle potential timezone issues if needed)
            # If Tip.date is DateTimeField, you might want to combine date and a default time
            cleaned_date = form.cleaned_data['date']
            if isinstance(cleaned_date, date) and not isinstance(cleaned_date, datetime):
                 # Combine with midnight time if model field is DateTimeField
                 # Adjust timezone logic if necessary (e.g., using settings.TIME_ZONE)
                 tip.date = datetime.combine(cleaned_date, datetime.min.time())
            else:
                 tip.date = cleaned_date # Assume it's already datetime or handled correctly

            tip.save()

            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Tip added successfully!'})
            else:
                # Redirect back to the calendar view for the month the tip was added to
                return redirect('user_tips', year=tip.date.year, month=tip.date.month)
        else: # Form is invalid
            if is_ajax:
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            else:
                # Re-render the full form page with errors
                # Pass context if your template needs it
                return render(request, 'myapp/add_tip_form.html', {'form': form})

    # Handle GET request (Show the form)
    elif request.method == 'GET':
        initial_data = {}
        date_str = request.GET.get('date')
        if date_str:
            try:
                # Use date directly, form widget handles display format
                initial_data['date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        form = TipForm(initial=initial_data)

        # If AJAX GET (less common for add, but possible), maybe return form HTML fragment?
        # For now, assume GET is for a full page load if not AJAX
        if is_ajax:
             # Decide what to return for AJAX GET - maybe not supported or return form snippet
             return JsonResponse({'error': 'AJAX GET not fully supported for add form'}, status=405)
        else:
             # Render the full page template
             return render(request, 'myapp/add_tip_form.html', {'form': form})

@login_required
@require_http_methods(["GET", "POST"])
def edit_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if tip.user != request.user:
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        else:
            return HttpResponseForbidden("You don't have permission to edit this tip.")

    if request.method == "POST":
        # TipForm now includes cash_made and hours_worked
        form = TipForm(request.POST, instance=tip)
        if form.is_valid():
            # Handle date conversion if needed
            cleaned_date = form.cleaned_data['date']
            if isinstance(cleaned_date, date) and not isinstance(cleaned_date, datetime):
                 tip.date = datetime.combine(cleaned_date, datetime.min.time())
                 # If using timezones:
                 # tip.date = timezone.make_aware(datetime.combine(cleaned_date, datetime.min.time()))
            # No else needed if form field correctly provides datetime

            # cash_made and hours_worked are updated automatically by form.save()
            form.save()

            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Tip updated successfully!'})
            else:
                return redirect('user_tips', year=tip.date.year, month=tip.date.month)
        else:
            if is_ajax:
                # form.errors will include errors for new fields if validation fails
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
            else:
                # Non-AJAX fallback (render form page with errors)
                # Ensure you have an 'edit_tip.html' template or adjust
                return render(request, 'myapp/tip_form.html', {'form': form, 'tip': tip}) # Assuming generic form template

    # --- Handle GET (Fetch Data for Modal or Show Form) ---
    elif request.method == "GET":
        if is_ajax:
            # *** MODIFIED: Include cash_made and hours_worked in JSON ***
            tip_data = model_to_dict(tip, fields=[
                'id', 'amount', 'gratuity', 'date', 'note',
                'cash_made', 'hours_worked' # Add the new fields here
            ])

            # Convert Decimals to strings for JSON compatibility
            tip_data['amount'] = str(tip_data['amount'])
            tip_data['gratuity'] = str(tip_data['gratuity']) if tip_data['gratuity'] is not None else '0.00'
            tip_data['cash_made'] = str(tip_data['cash_made']) if tip_data['cash_made'] is not None else '0.00'
            tip_data['hours_worked'] = str(tip_data['hours_worked']) if tip_data['hours_worked'] is not None else '0.00'

            # Format date consistently (ISO format is good for JS)
            if isinstance(tip_data['date'], datetime):
                 tip_data['date'] = tip_data['date'].isoformat()
            elif isinstance(tip_data['date'], date):
                 tip_data['date'] = tip_data['date'].isoformat()

            return JsonResponse({'tip': tip_data})
        else:
            # Render the full edit form page for non-AJAX access
            form = TipForm(instance=tip)
            # Ensure you have an 'edit_tip.html' template or adjust
            return render(request, 'myapp/tip_form.html', {'form': form, 'tip': tip}) # Assuming generic form template



# --- UPDATED delete_tip view ---
@login_required
@require_http_methods(["GET", "POST", "DELETE"]) # Allow GET (confirmation), POST (form confirm), DELETE (AJAX)
def delete_tip(request, tip_id):
    tip = get_object_or_404(Tip, id=tip_id) # Get tip first
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    # --- Permission Check ---
    if tip.user != request.user:
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        else:
            return HttpResponseForbidden("You don't have permission to delete this tip.")

    # --- Handle AJAX DELETE request ---
    if request.method == 'DELETE' and is_ajax:
        try:
            tip_year = tip.date.year # Get before deleting
            tip_month = tip.date.month
            tip.delete()
            return JsonResponse({'status': 'success', 'message': 'Tip deleted successfully.'})
        except Exception as e:
            # Log the error e
            print(f"Error deleting tip {tip_id} via AJAX: {e}") # Basic logging
            return JsonResponse({'status': 'error', 'message': 'Could not delete tip due to a server error.'}, status=500)

    # --- Handle POST request (from confirmation form) ---
    elif request.method == 'POST':
        try:
            tip_year = tip.date.year
            tip_month = tip.date.month
            tip.delete()
            # Add success message for non-AJAX if using Django messages framework
            # messages.success(request, 'Tip deleted successfully.')
            return redirect('user_tips', year=tip_year, month=tip_month)
        except Exception as e:
             # Log the error e
             print(f"Error deleting tip {tip_id} via POST: {e}")
             # Add error message if using Django messages
             # messages.error(request, 'Could not delete tip.')
             # Redirect back to the confirmation page or the tips page
             return redirect('user_tips', year=tip.date.year, month=tip.date.month)


    # --- Handle GET request (show confirmation page) ---
    elif request.method == 'GET':
        # If AJAX GET for delete URL (less common, but possible), return error or confirmation data
        if is_ajax:
             return JsonResponse({'status': 'error', 'message': 'Use DELETE method for AJAX deletion.'}, status=405) # Method Not Allowed
        else:
             # Render the confirmation template for non-AJAX GET
             # Ensure you have 'myapp/confirm_delete_tip.html' or similar
             return render(request, 'myapp/confirm_delete.html', {'tip': tip})

    # Fallback for unexpected methods (though require_http_methods should prevent this)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
