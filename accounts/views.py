from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import UserRegistrationForm, UserLoginForm

def register_view(request):
    if request.user.is_authenticated:
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
        if request.user.is_owner() and request.user.is_owner_approved:
            return redirect('owner_home')
        return redirect('home')
        
    role_param = request.GET.get('role', 'PLAYER').upper()
    current_role = role_param if role_param in ['PLAYER', 'OWNER'] else 'PLAYER'

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        submitted_role = request.POST.get('role', current_role).upper()
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
                
            if user.is_owner():
                if not user.is_owner_approved and not user.is_superuser:
                    messages.info(request, 'Your owner account is awaiting administrator approval.')
                    return redirect('home')
                messages.success(request, f'Welcome to Ground Owner Hub, {user.username}!')
                return redirect('owner_home')
            else:
                if submitted_role == 'OWNER':
                    messages.info(request, f'Welcome back, {user.username}! You signed in with a Player account. To manage grounds, register an Owner account.')
                else:
                    messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
            current_role = submitted_role
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {
        'form': form,
        'role': current_role,
        'is_owner_login': (current_role == 'OWNER')
    })

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
            login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
                
            if user.is_owner():
                if not user.is_owner_approved and not user.is_superuser:
                    messages.info(request, 'Your owner account is awaiting administrator approval.')
                    return redirect('home')
                messages.success(request, f'Welcome to Ground Owner Hub, {user.username}!')
                return redirect('owner_home')
            else:
                messages.warning(request, f'Welcome {user.username}! You are registered as a Player. Directing you to the player portal.')
                return redirect('home')
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

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
