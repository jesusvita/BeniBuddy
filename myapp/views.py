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
    from django.utils import timezone
    today_date = timezone.localdate()  # Timezone aware

    current_year, current_month = today_date.year, today_date.month

    # Use provided year/month or default to current
    year = int(year) if year else current_year
    month = int(month) if month else current_month

    # Validate month
    if not (1 <= month <= 12):
        month = current_month

    # Month navigation
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    try:
        first_day_month = date(year, month, 1)
        last_day_val = calendar.monthrange(year, month)[1]
        last_day_month = date(year, month, last_day_val)
    except ValueError:
        return redirect('user_tips')

    # Fetch tips for the month
    monthly_tips = Tip.objects.filter(
        user=request.user,
        date__date__range=[first_day_month, last_day_month]
    ).order_by('date')

    # Aggregate monthly totals
    monthly_aggregation = monthly_tips.aggregate(
        total_tip=Coalesce(Sum('amount'), decimal.Decimal('0.00'), output_field=DecimalField()),
        total_gratuity=Coalesce(Sum('gratuity'), decimal.Decimal('0.00'), output_field=DecimalField()),
        total_cash=Coalesce(Sum('cash_made'), decimal.Decimal('0.00'), output_field=DecimalField()),
        total_hours=Coalesce(Sum('hours_worked'), decimal.Decimal('0.00'), output_field=DecimalField())
    )

    total_monthly_tip = monthly_aggregation['total_tip']
    total_monthly_gratuity = monthly_aggregation['total_gratuity']
    total_monthly_cash = monthly_aggregation['total_cash']
    total_monthly_hours = monthly_aggregation['total_hours']

    total_monthly_earnings = (
        (total_monthly_tip or 0) +
        (total_monthly_gratuity or 0) +
        (total_monthly_cash or 0)
    )

    # Prepare tips dict keyed by date for quick lookup
    tip_dict = {tip.date.date(): tip for tip in monthly_tips}

    # Generate calendar grid weeks with Sunday first
    cal = calendar.Calendar(firstweekday=6)
    weeks = []
    for week_dates in cal.monthdatescalendar(year, month):
        week_data = []
        for day_date in week_dates:
            if day_date.month == month:
                tip_for_day = tip_dict.get(day_date)
                week_data.append({
                    'day': day_date.day,
                    'tip': tip_for_day,
                    'date': day_date.strftime('%Y-%m-%d'),
                })
            else:
                week_data.append(None)
        weeks.append(week_data)

    # Paycheck cycle data (unchanged)
    paycheck_cycle, _ = PaycheckCycle.objects.get_or_create(user=request.user)

    # --- Paycheck Estimation Logic ---
    paycheck_day_display = None
    recent_total_tip = decimal.Decimal('0.00')
    recent_total_gratuity = decimal.Decimal('0.00')
    recent_total_cash = decimal.Decimal('0.00')
    recent_total_hours = decimal.Decimal('0.00')
    paycheck_total = decimal.Decimal('0.00')

    if paycheck_cycle and paycheck_cycle.start_date and paycheck_cycle.frequency:
        # This logic determines the current or next pay period based on the cycle settings
        # and calculates totals for that period.
        period_start_date = None
        period_end_date = None

        if paycheck_cycle.frequency == PaycheckCycle.PayFrequency.BIWEEKLY:
            # Example logic for bi-weekly cycle
            # You might need more sophisticated logic to find the *current* or *next upcoming* period
            # This example finds the period that would contain today_date or the one just after cycle.start_date
            cycle_anchor_date = paycheck_cycle.start_date
            days_from_anchor = (today_date - cycle_anchor_date).days

            if days_from_anchor < 0: # today_date is before the cycle anchor
                period_start_date = cycle_anchor_date
            else:
                # Calculate how many full 14-day segments from the anchor date to get to the current period's start
                num_segments = days_from_anchor // 14
                period_start_date = cycle_anchor_date + timedelta(days=num_segments * 14)
            
            period_end_date = period_start_date + timedelta(days=13)
            # Calculate the actual payday, 5 days after the period ends
            paycheck_day_display = period_end_date + timedelta(days=5)

            recent_tips_qs = Tip.objects.filter(
                user=request.user,
                date__date__range=[period_start_date, period_end_date]
            )
            recent_aggregation = recent_tips_qs.aggregate(
                sum_tip=Coalesce(Sum('amount'), decimal.Decimal('0.00')),
                sum_gratuity=Coalesce(Sum('gratuity'), decimal.Decimal('0.00')),
                sum_cash=Coalesce(Sum('cash_made'), decimal.Decimal('0.00')),
                sum_hours=Coalesce(Sum('hours_worked'), decimal.Decimal('0.00'))
            )
            recent_total_tip = recent_aggregation['sum_tip']
            recent_total_gratuity = recent_aggregation['sum_gratuity']
            recent_total_cash = recent_aggregation['sum_cash']
            recent_total_hours = recent_aggregation['sum_hours']
            paycheck_total = recent_total_tip + recent_total_gratuity + recent_total_cash # Adjust as per your total definition

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
        "total_monthly_cash": total_monthly_cash,
        "total_monthly_hours": total_monthly_hours,
        "total_monthly_earnings": total_monthly_earnings,
        "paycheck_cycle": paycheck_cycle,
        "paycheck_day": paycheck_day_display,
        "recent_total_tip": recent_total_tip,
        "recent_total_gratuity": recent_total_gratuity,
        "recent_total_cash": recent_total_cash,
        "recent_total_hours": recent_total_hours,
        "paycheck_total": paycheck_total,
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

def benihana_qr_view(request):
    """Renders the Benihana QR code page."""
    return render(request, 'myapp/benihanaQR.html')
