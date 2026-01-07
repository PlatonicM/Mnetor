from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Courses, MyCourse

# 🛠️ HELPER — Centralized Price & Data Logic
def get_cart_data(request):
    cart = request.session.get("cart", [])
    items = Courses.objects.filter(id__in=cart)
    
    total = sum(i.price for i in items)
    gst = round(total * 0.18, 2)
    final_total = round(total + gst, 2)
    
    return {
        "items": items,
        "total": total,
        "gst": gst,
        "final_total": final_total,
        "cart_count": len(items),
    }

# 🛒 ADD TO CART (AJAX Compatible)
@login_required
def add_to_cart(request, cid):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    cart = request.session.get("cart", [])

    if cid not in cart:
        cart.append(cid)
        request.session["cart"] = cart
        request.session.modified = True
        return JsonResponse({
            "success": True, 
            "msg": "Track added to bag",
            "cart_count": len(cart)
        })

    return JsonResponse({"success": False, "msg": "Already in your bag"})

# 🛒 CART PAGE
@login_required
def cart_page(request):
    data = get_cart_data(request)
    return render(request, "cart.html", data)

# ❌ REMOVE FROM CART (AJAX Compatible)
@login_required
def remove_from_cart(request, cid):
    cart = request.session.get("cart", [])
    cid_str = int(cid) # Ensure ID matching

    if cid_str in cart:
        cart.remove(cid_str)
        request.session["cart"] = cart
        request.session.modified = True

    # If AJAX request, return new totals for the UI
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = get_cart_data(request)
        return JsonResponse({
            "success": True,
            "cart_count": data['cart_count'],
            "total": data['total'],
            "gst": data['gst'],
            "final_total": data['final_total']
        })

    messages.success(request, "Track removed from bag")
    return redirect("cart_page")

# 💳 CHECKOUT PAGE
@login_required
def checkout_page(request):
    data = get_cart_data(request)

    if data['cart_count'] == 0:
        messages.warning(request, "Your selection is empty.")
        return redirect("cart_page")

    return render(request, "checkout.html", data)

# 💰 PROCESS ENROLLMENT (Final Redirect)
@login_required
def process_checkout(request):
    if request.method != "POST":
        return redirect("checkout_page")

    data = get_cart_data(request)

    if data['cart_count'] == 0:
        messages.error(request, "Your session has expired or cart is empty.")
        return redirect("cart_page")

    # 🎉 Handshake: Convert Cart Items → MyCourse (Access Granted)
    for course in data['items']:
        MyCourse.objects.get_or_create(
            user=request.user,
            course=course
        )

    # Clear session cart after successful enrollment
    request.session["cart"] = []
    
    # Store purchased items in a temp context for the success page
    context = {
        "items": data['items'],
        "final_total": data['final_total'],
        "order_id": f"MLMS-{request.user.id}-{data['items'][0].id}" # Example Order ID
    }

    return render(request, "checkout_success.html", context)