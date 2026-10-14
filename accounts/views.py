from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import InstitutionRegistrationForm, UserRegistrationForm, UserLoginForm


def _safe_next_url(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None

def register_view(request):
    if request.user.is_authenticated:
        if request.user.is_institution_coordinator():
            return redirect('institution_dashboard')
        return redirect('owner_home' if request.user.is_owner() and request.user.is_owner_approved else 'home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.is_owner():
                user.is_owner_approved = False
                user.owner_terms_accepted_at = timezone.now()
                user.save(update_fields=['is_owner_approved', 'owner_terms_accepted_at'])
            login(request, user)
            messages.success(request, f'Welcome to GroundX, {user.username}! Account created successfully.')
            if user.is_owner():
                if not user.is_owner_approved and not user.is_superuser:
                    messages.info(request, 'Your owner account is awaiting administrator approval.')
                    return redirect('home')
                return redirect('owner_home')
            if user.is_institution_coordinator():
                return redirect('institution_dashboard')
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        role_param = request.GET.get('role', 'PLAYER').upper()
        initial_role = role_param if role_param in ['PLAYER', 'OWNER'] else 'PLAYER'
        form = UserRegistrationForm(initial={'role': initial_role})
        
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        if request.user.is_owner() and request.user.is_owner_approved:
            return redirect('owner_home')
        return redirect('home')
        
    role_param = request.GET.get('role', 'PLAYER').upper()
    current_role = role_param if role_param in ['PLAYER', 'OWNER', 'INSTITUTION'] else 'PLAYER'

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        submitted_role = request.POST.get('role', current_role).upper()
        if submitted_role not in {'PLAYER', 'OWNER', 'INSTITUTION'}:
            submitted_role = current_role
        current_role = submitted_role
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                messages.error(request, 'Administrator accounts must use the administrator sign-in page.')
            elif user.role != submitted_role:
                selected_role_name = {
                    'PLAYER': 'Player',
                    'OWNER': 'Turf Owner',
                    'INSTITUTION': 'Coordinator',
                }[submitted_role]
                messages.error(
                    request,
                    f'This account is registered as {user.get_role_display()}, but you selected {selected_role_name}. '
                    f'Select the {user.get_role_display()} sign-in option to continue.',
                )
            else:
                login(request, user)
                next_url = _safe_next_url(request)
                if next_url:
                    return redirect(next_url)

                if user.is_owner():
                    if not user.is_owner_approved:
                        messages.info(request, 'Your owner account is awaiting administrator approval.')
                        return redirect('home')
                    messages.success(request, f'Welcome to Ground Owner Hub, {user.username}!')
                    return redirect('owner_home')
                if user.is_institution_coordinator():
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('institution_dashboard')
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {
        'form': form,
        'role': current_role,
        'is_owner_login': (current_role == 'OWNER'),
        'is_institution_login': (current_role == 'INSTITUTION'),
    })


def institution_register_view(request):
    if request.user.is_authenticated:
        return redirect('institution_dashboard' if request.user.is_institution_coordinator() else 'home')
    if request.method == 'POST':
        form = InstitutionRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to GroundX, {user.institution_profile.name}!')
            return redirect('institution_dashboard')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = InstitutionRegistrationForm()
    return render(request, 'accounts/institution_register.html', {'form': form})


def institution_login_view(request):
    if request.user.is_authenticated:
        return redirect('institution_dashboard' if request.user.is_institution_coordinator() else 'home')
    return redirect('/accounts/login/?role=institution')

def admin_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        messages.info(request, 'Sign out of your current account before signing in as an administrator.')
        return redirect('home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser:
                login(request, user)
                messages.success(request, 'Administrator sign-in successful.')
                return redirect('admin_dashboard')
            messages.error(request, 'This account does not have administrator access.')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/admin_login.html', {'form': form})

def owner_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_owner() and request.user.is_owner_approved:
            return redirect('owner_home')
        messages.info(request, f'You are currently signed in as {request.user.username} (Player). Sign out to switch to a Ground Owner account.')
        return redirect('home')
        
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.is_owner():
                messages.error(
                    request,
                    f'This account is registered as {user.get_role_display()}, not Turf Owner. '
                    'Choose the matching sign-in option to continue.',
                )
            else:
                login(request, user)
                next_url = _safe_next_url(request)
                if next_url:
                    return redirect(next_url)
                if not user.is_owner_approved:
                    messages.info(request, 'Your owner account is awaiting administrator approval.')
                    return redirect('home')
                messages.success(request, f'Welcome to Ground Owner Hub, {user.username}!')
                return redirect('owner_home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {
        'form': form,
        'role': 'OWNER',
        'is_owner_login': True
    })


@login_required
def accept_owner_terms_view(request):
    if not request.user.is_owner():
        messages.error(request, 'Owner terms are available to Ground Owner accounts.')
        return redirect('home')
    if not request.user.is_owner_approved:
        messages.info(request, 'Your owner account is awaiting administrator approval.')
        return redirect('home')
    if request.method == 'POST' and request.POST.get('accept_terms') == 'yes':
        request.user.owner_terms_accepted_at = timezone.now()
        request.user.save(update_fields=['owner_terms_accepted_at'])
        messages.success(request, 'Owner terms accepted. You can now manage your grounds.')
        return redirect('owner_home')
    return render(request, 'accounts/owner_terms.html')

@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
