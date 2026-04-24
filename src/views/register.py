from django.shortcuts import render, redirect
from ..forms import RegisterForm
from django.contrib.auth import login

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            login(request, user)
            return redirect('/')

    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})