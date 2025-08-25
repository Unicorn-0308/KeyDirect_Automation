from selenium import webdriver
from selenium.common import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
import os
import tempfile
import sys

class ShopifyLogin:
    def __init__(self, headless=False):
        self.headless = headless
        self.install(headless=headless)

    def install(self, headless=False):
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1080,720")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Better user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Create a unique user data directory to avoid conflicts
        self.user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
        chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")
        
        # Initialize driver with better error handling
        self.driver = None
        initialization_methods = [
            ("WebDriver Manager", self._init_with_manager, chrome_options),
            ("System Chrome", self._init_system_chrome, chrome_options),
            ("Direct Chrome", self._init_direct_chrome, chrome_options)
        ]
        
        for method_name, method, options in initialization_methods:
            try:
                print(f"Trying to initialize Chrome with: {method_name}")
                self.driver = method(options)
                if self.driver:
                    print(f"Successfully initialized Chrome with: {method_name}")
                    break
            except Exception as e:
                print(f"Failed with {method_name}: {str(e)}")
                continue
        
        if not self.driver:
            raise WebDriverException(
                "Failed to initialize Chrome WebDriver. Please ensure Chrome and ChromeDriver are installed.\n"
                "You can install ChromeDriver manually or let webdriver-manager handle it automatically."
            )
        
        self.wait = WebDriverWait(self.driver, 180)
    
    def _init_with_manager(self, options):
        """Initialize Chrome using webdriver-manager to auto-download the driver"""
        try:
            service = Service(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"WebDriver Manager error: {e}")
            raise
    
    def _init_system_chrome(self, options):
        """Try to use Chrome from system PATH"""
        return webdriver.Chrome(options=options)
    
    def _init_direct_chrome(self, options):
        """Try common Chrome installation paths on Windows"""
        common_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        for chrome_path in common_paths:
            if os.path.exists(chrome_path):
                options.binary_location = chrome_path
                # Try to find or download ChromeDriver
                try:
                    service = Service(ChromeDriverManager().install())
                    return webdriver.Chrome(service=service, options=options)
                except:
                    return webdriver.Chrome(options=options)
        
        raise FileNotFoundError("Chrome not found in common installation paths")
    
    def login(self, store_url, email, password):
        """
        Login to Shopify store
        """
        try:
            self.close()
            self.install(self.headless)


            # Navigate to login page
            login_url = f"{store_url}/account/login"
            print(f"Navigating to: {login_url}")
            self.driver.get(login_url)

            print("\n=== Attempting Login ===")
            
            # Strategy 1: Try targeting specific Shopify login fields by ID
            try:
                print("Trying strategy: Targeting specific Shopify fields by ID")
                
                # Wait for page to load
                time.sleep(2)
                
                # Try to switch to iframe if it exists
                iframe_found = False
                try:
                    self.driver.switch_to.frame("advancedRegForm")
                    iframe_found = True
                    print("Switched to iframe 'advancedRegForm'")
                except:
                    print("No iframe found, continuing on main page")
                
                # Execute login script
                self.driver.execute_script("""
                    var emailField = document.querySelectorAll('input[name="email"]')[0];
                    console.log(emailField);
                    emailField.value = arguments[0];
                    emailField.dispatchEvent(new Event('input', { bubbles: true }));
                    emailField.dispatchEvent(new Event('change', { bubbles: true }));
                    var passField = document.querySelectorAll('input[name="password"]')[0];
                    console.log(passField);
                    passField.value = arguments[1];
                    passField.dispatchEvent(new Event('input', { bubbles: true }));
                    passField.dispatchEvent(new Event('change', { bubbles: true }));
                    document.querySelectorAll('button[style="width: 100%; margin-top: 1em; background-color: rgb(31, 69, 194) !important;"]')[0].click();
                """, email, password)

                print("Waiting for login to complete")

                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cart-count-bubble")))
                print("\n=== Login Success ===")
                
            except Exception as e1:
                print(f"Strategy failed: {str(e1)}")

            try:
                old_element = self.driver.find_element(By.CLASS_NAME, "cart-count-bubble")
                self.wait.until(EC.staleness_of(old_element))
                print("\n=== Reload Starts ===")
            except Exception as e2:
                print(f"\n=== Reload failed ===")

            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cart-count-bubble")))
            print("\n=== Reload Success ===")
            
            # Check if login was successful
            current_url = self.driver.current_url
            print(f"Current URL after login attempt: {current_url}")
            
            # Check various success indicators
            success_indicators = [
                "/account" in current_url,
                "/challenge" in current_url,
                "/cart" in current_url and login_url not in current_url,  # Redirected to cart after login
                "/checkout" in current_url,
                "welcome" in self.driver.page_source.lower(),
                "logout" in self.driver.page_source.lower(),  # Logout link appears when logged in
                "sign out" in self.driver.page_source.lower()
            ]
            
            if any(success_indicators):
                self.driver.get(f"{store_url}/cart")

                print("Login successful!")
                    
                return True
            else:
                print("Login may have failed. Check the browser window.")
                return False
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_cookies(self):
        """
        Get all cookies from the current session
        """
        try:
            cookies = self.driver.get_cookies()
            return cookies
        except Exception as e:
            print(f"Error getting cookies: {str(e)}")
            return []
    
    def save_cookies_to_file(self, filename="shopify_cookies.json"):
        """
        Save cookies to a JSON file
        """
        cookies = self.get_cookies()
        try:
            with open(filename, 'w') as f:
                json.dump(cookies, f, indent=4)
            print(f"Cookies saved to {filename}")
            return True
        except Exception as e:
            print(f"Error saving cookies: {str(e)}")
            return False
    
    def load_cookies_from_file(self, filename="shopify_cookies.json"):
        """
        Load cookies from a JSON file
        """
        try:
            with open(filename, 'r') as f:
                cookies = json.load(f)
            
            # Add cookies to current session
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            
            print(f"Cookies loaded from {filename}")
            return True
        except Exception as e:
            print(f"Error loading cookies: {str(e)}")
            return False
    
    def print_cookies(self):
        """
        Print all cookies in a readable format
        """
        cookies = self.get_cookies()
        print("\n=== COOKIES ===")
        for cookie in cookies:
            print(f"Name: {cookie['name']}")
            print(f"Value: {cookie['value']}")
            print(f"Domain: {cookie['domain']}")
            print(f"Path: {cookie['path']}")
            print(f"Secure: {cookie['secure']}")
            print("-" * 50)

    def add_products(self, productUrl, qty):
        """
        Add products to the cart
        """
        try:
            # Navigate to the product page
            if self.driver.current_url != productUrl:
                print(f"Navigating to product: {productUrl}")
                self.driver.get(productUrl)
            else:
                print(f"Already on product: {self.driver.current_url}")
                
            # Execute login script
            self.driver.execute_script("""
                var qtyField = document.querySelectorAll('input[name="quantity"][type="number"]')[0];
                console.log(qtyField);
                qtyField.value = arguments[0];
                qtyField.dispatchEvent(new Event('input', { bubbles: true }));
                qtyField.dispatchEvent(new Event('change', { bubbles: true }));
            """, qty)
            time.sleep(0.5)
            button = self.driver.find_element(By.CSS_SELECTOR, 'div.product-form__buttons>button')
            button.click()
            print(f"Added {qty} of {productUrl}")
            return True
                
        except Exception as e:
            print(f"Error adding product: {str(e)}")
            return False
    
    def close(self):
        """
        Close the browser and cleanup temporary user data directory
        """
        del self.wait
        self.driver.quit()
        # Cleanup temporary user data directory
        try:
            import shutil
            if hasattr(self, 'user_data_dir') and os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir)
                print(f"Cleaned up temporary directory: {self.user_data_dir}")
        except Exception as e:
            print(f"Warning: Could not cleanup temporary directory: {e}")

# Usage example
if __name__ == "__main__":
    # Initialize the login class
    shopify = ShopifyLogin(headless=True)  # Set to True for headless mode
    
    # Store credentials
    STORE_URL = "https://www.uhs-hardware.com"  # Replace with actual store URL
    EMAIL = "ja@autokey.ca"  # Replace with your email
    PASSWORD = "MfeC3ScnMMxLR:!"  # Replace with your password
    
    try:
        # Login to the store
        if shopify.login(STORE_URL, EMAIL, PASSWORD):
            # Get and print cookies
            shopify.print_cookies()
            
            # Save cookies to file
            shopify.save_cookies_to_file("my_shopify_cookies.json")
            
            print(f"Current URL: {shopify.driver.current_url}")
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Close browser
        time.sleep(5)  # Keep browser open for 5 seconds to see results
        shopify.close()
