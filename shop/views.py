from ast import Or
import email
from itertools import product
import re
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import *
import json
import datetime
from .utils import cookieCart, cartData, guestOrder
from .forms import OrderForm, CreateUserForm
# from .filters import OrderFilter

def registerPage(request):
	# form = CreateUserForm()

	if request.method == 'POST':
		form = CreateUserForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user) # follow the docs
			username = form.cleaned_data.get('username')
			messages.success(request, 'Account was created for ' + username)
			return redirect('login')
		messages.error(request, "Unsuccessful registration. Invalid information.")
	form = CreateUserForm()
	context = {'form':form}
	return render(request, 'shop/register.html', context)


def loginPage(request):
	if request.method == "POST":
		form = authenticate(request, data=request.POST)
		if form.is_valid():
			username = form.cleaned_data.get('username')
			password = form.cleaned_data.get('password')
			user = authenticate(username=username, password=password)
			if user is not None:
				login(request, user)
				messages.info(request, f"You are now logged in as {username}.")
				return redirect("shop")
			else:
				messages.error(request,"Invalid username or password.")
		else:
			messages.error(request,"Invalid username or password.")
	form = authenticate()
	return render(request=request, template_name="shop/login.html", context={"login_form":form})

def logoutUser(request):
	logout(request)
	messages.info(request, "You have successfully logged out.")
	return redirect('shop')

def shop(request):
	data = cartData(request)
	cartItems = data['cartItems']

	products = Product.objects.all()
	context = {'products':products, 'cartItems':cartItems}
	return render(request, 'shop/store.html', context)

def cart(request):
	data = cartData(request)
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'shop/cart.html', context)


def checkout(request):
	data = cartData(request)
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'shop/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)
	
	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)

	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)

	else:
		customer, order = guestOrder(request, data)

	total = float(data['form']['total'])
	order.transaction_id = transaction_id
	
	if total == float(order.get_cart_total):
		order.complete = True
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
				customer=customer,
				order=order,
				address=data['shipping']['address'],
				city=data['shipping']['city'],
				state=data['shipping']['state'],
				zipcode=data['shipping']['zipcode'],
			)
	
	return JsonResponse('Payment complete!', safe=False)
