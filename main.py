import requests
from fastapi import FastAPI, Response
from pydantic import BaseModel
import json
import traceback

STORE_URL = "https://keydirect.ca"  # Replace with actual store URL

session = requests.Session()
cookies = {}

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

@app.post("/login")
async def login(account: Account):
    global cookies, session

    cookies = {}

    try:
        session.close()
        session = requests.Session()

        # Find nonce
        response = session.get(f"{STORE_URL}/my-account/")

        start = response.text.find("name=\"woocommerce-login-nonce\" value=\"")
        end = response.text.find("\" />", start)
        nonce = response.text[start+38:end]

        data = {
            'username': account.email,
            'password': account.password,
            'rememberme': 'forever',
            'woocommerce-login-nonce': nonce,
            '_wp_http_referer': '/my-account/',
            'login': 'Log in',
            'redirect': 'https://keydirect.ca/'
        }
        print(data)

        response = session.post(f"{STORE_URL}/my-account/", data=data)


        for cookie in session.cookies.items():
            cookies[cookie[0]] = cookie[1]

        return Response(content=json.dumps({"status": "success", "cookies": cookies}), media_type="application/json")
    except Exception as e:
        error_msg = f"Login error: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return Response(content=json.dumps({"status": "fail", "msg": error_msg}), media_type="application/json")


@app.post("/addProduct")
async def addProduct(product: Product):
    global cookies, session

    try:
        # Find product id
        response = session.get(product.url)

        start = response.text.find("name=\"add-to-cart\" value=\"")
        end = response.text.find("\" class=", start)
        id = int(response.text[start+26:end])

        # Add product to cart
        data = {
            'tm-epo-counter': 1,
            'tcaddtocart': id,
            'thwepof_product_fields': '',
            'quantity': product.quantity,
            'add-to-cart': id,
            'action': 'xoo_wsc_add_to_cart',
        }

        session.post(f"{STORE_URL}/?wc-ajax=xoo_wsc_add_to_cart/", data=data)

        for cookie in session.cookies.items():
            cookies[cookie[0]] = cookie[1]

        return Response(content=json.dumps({"status": "success", "cookies": cookies}), media_type="application/json")
        
    except Exception as e:
        error_msg = f"Failed to add product: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        return Response(
            content=json.dumps({"status": "fail", "msg": error_msg}),
            media_type="application/json"
        )


