from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm

def register_view(request):
    if request.user.is_authenticated:
        return redirect('owner_home' if request.user.is_owner() else 'home')
        
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to GroundX, {user.username}! Account created successfully.')
            if user.is_owner():
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
        if request.user.is_owner():
            return redirect('owner_home')
        return redirect('home')
        
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.is_owner():
                return redirect('owner_home')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
        
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
