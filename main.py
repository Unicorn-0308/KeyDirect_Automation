import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel
from extract import ShopifyLogin
import os
import json
import traceback

# Initialize ShopifyLogin with error handling
shopify = None
try:
    shopify = ShopifyLogin(headless=False)
    print("ShopifyLogin initialized successfully")
except Exception as e:
    print(f"Warning: Failed to initialize ShopifyLogin on startup: {str(e)}")
    print("Will attempt to initialize on first request")

cart = ""
cookies = {}

#
app = FastAPI()

class Account(BaseModel):
    email: str
    password: str

class Product(BaseModel):
    url: str
    quantity: int = 1

@app.get("/")
async def root():
    return {"message": "Hello World. Welcome to FastAPI!"}

@app.get("/updateCookie")
async def updateCookie():
    global cart, cookies, shopify

    cookie_str = ""
    for cookie in shopify.get_cookies():
        cookie_str += f"{cookie['name']}={cookie['value']}; "

    if not cart:
        return {"status": "fail", "msg": "No cookie stored. Plz login first."}

    url = "https://www.uhs-hardware.com/cart/update.js"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_str
    }
    data = {"note": ""}

    try:
        response = requests.post(url, headers=headers, data=data)

        for cookie in response.cookies:
            cookies[cookie.name] = cookie.value

        return Response(content=json.dumps({"status": "success", "cookie": cart, "cookies": cookies}), media_type="application/json")
    
    except Exception as e:
        return Response(content=json.dumps({"status": "fail", "msg": str(e)}), media_type="application/json")

@app.post("/getCookie")
async def getCookie(account: Account):
    global cart, cookies, shopify

    # Try to initialize ShopifyLogin if not already done
    if shopify is None:
        try:
            shopify = ShopifyLogin(headless=False)
            print("ShopifyLogin initialized on demand")
        except Exception as e:
            error_msg = f"Failed to initialize WebDriver: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            return Response(
                content=json.dumps({"status": "fail", "msg": error_msg}), 
                media_type="application/json"
            )

    STORE_URL = "https://www.uhs-hardware.com"  # Replace with actual store URL

    try:
        if shopify.login(STORE_URL, account.email, account.password):
            for cookie in shopify.get_cookies():
                cookies[cookie["name"]] = cookie["value"]
                if cookie["name"] == "cart":
                    cart = cookie["value"]

            cookie_str = ""
            for cookie in shopify.get_cookies():
                cookie_str += f"{cookie['name']}={cookie['value']}; "

            print(cookie_str)

            return Response(content=json.dumps({"status": "success", "cookie": cart, "cookies": cookies}), media_type="application/json")
        else:
            return Response(content=json.dumps({"status": "fail", "msg": "Login failed"}), media_type="application/json")
    except Exception as e:
        error_msg = f"Login error: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return Response(content=json.dumps({"status": "fail", "msg": error_msg}), media_type="application/json")

@app.post("/addProduct")
async def addProduct(product: Product):
    global shopify
    
    # Check if ShopifyLogin is initialized
    if shopify is None:
        return Response(
            content=json.dumps({"status": "fail", "msg": "ShopifyLogin not initialized. Please login first."}),
            media_type="application/json"
        )
    
    try:
        # Add product to cart
        if shopify.add_products(product.url, product.quantity):
            # Get updated cookies
            updated_cookies = {}
            updated_cart = ""
            for cookie in shopify.get_cookies():
                updated_cookies[cookie["name"]] = cookie["value"]
                if cookie["name"] == "cart":
                    updated_cart = cookie["value"]
            
            return Response(
                content=json.dumps({
                    "status": "success", 
                    "msg": f"Product added to cart with quantity {product.quantity}",
                    "cart": updated_cart,
                    "cookies": updated_cookies
                }),
                media_type="application/json"
            )
        else:
            return Response(
                content=json.dumps({"status": "fail", "msg": "Failed to add product"}),
                media_type="application/json"
            )
        
    except Exception as e:
        error_msg = f"Failed to add product: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return Response(
            content=json.dumps({"status": "fail", "msg": error_msg}),
            media_type="application/json"
        )


