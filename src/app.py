import base64
import hashlib
import logging
import secrets
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import flet as ft

from config import SUPABASE_ANON_KEY, SUPABASE_URL
from core.supabase import SupabaseClient
from views import screens

log = logging.getLogger("app.pos")


class NoblePOSApp:
    def __init__(self, page: ft.Page, preferences: ft.SharedPreferences, file_picker: ft.FilePicker):
        self.page = page
        self.preferences = preferences
        self.file_picker = file_picker
        self.api = SupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.session = None
        self.shop = None
        self.role = "owner"
        self.selected_screen = "Checkout"
        self.status = ""
        self.inventory = []
        self.customers = []
        self.sales = []
        self.expenses = []
        self.team = []
        self.cart = []
        self.search_query = ""
        self.editing_item = None
        self.invite_code = ""
        self.receipt_text = ""
        self.page.title = "Noble POS Cloud"

    async def start(self):
        if not self.api.configured:
            self.status = "Supabase is not connected. Add your project URL and public anon key in src/config.py."
            self.render_auth()
            return
        if await self.complete_google_callback():
            return
        await self.restore_session()
        if self.session:
            await self.load_workspace()
        else:
            self.render_auth()

    async def restore_session(self):
        access = await self.preferences.get("noble_access_token")
        refresh = await self.preferences.get("noble_refresh_token")
        if not access:
            return
        self.api.access_token = access
        self.api.refresh_token = refresh
        try:
            user = await self.api.get_user(access)
            self.api.user_id = user["id"]
            self.session = {"access_token": access, "refresh_token": refresh, "user": user}
            return
        except Exception as first_error:
            if not refresh:
                log.info("Stored session expired: %s", first_error)
                await self.clear_session()
                return
            log.info("Refreshing stored session after %s", first_error)
        try:
            await self.accept_session(await self.api.refresh_session(refresh))
        except Exception as error:
            log.info("Session refresh failed: %s", error)
            await self.clear_session()

    async def accept_session(self, data):
        access = data.get("access_token")
        refresh = data.get("refresh_token")
        user = data.get("user") or {}
        if not access or not user.get("id"):
            raise RuntimeError("Supabase did not return an active session. Confirm your email if email confirmation is enabled.")
        self.session = {"access_token": access, "refresh_token": refresh, "user": user}
        self.api.access_token = access
        self.api.refresh_token = refresh
        self.api.user_id = user["id"]
        await self.preferences.set("noble_access_token", access)
        if refresh:
            await self.preferences.set("noble_refresh_token", refresh)

    async def clear_session(self):
        self.session = None
        self.shop = None
        self.api.access_token = None
        self.api.refresh_token = None
        self.api.user_id = None
        await self.preferences.remove("noble_access_token")
        await self.preferences.remove("noble_refresh_token")

    def render_auth(self):
        self.page.clean()
        self.page.add(screens.auth_screen(
            self.page, self.status, self.sign_in, self.sign_up,
            self.start_google_sign_in, self.api.configured,
        ))

    async def start_google_sign_in(self, full_name="", shop_name="", invite_code="", is_signup=False):
        full_name = (full_name or "").strip()
        shop_name = (shop_name or "").strip()
        invite_code = (invite_code or "").strip()
        if is_signup:
            if not full_name:
                self.status = "Enter your name before continuing with Google."
                self.render_auth()
                return
            if bool(shop_name) == bool(invite_code):
                self.status = "Enter a shop name to create a shop, or an invite code to join an existing shop."
                self.render_auth()
                return
            if shop_name:
                await self.preferences.set("noble_pending_shop_name", shop_name)
                await self.preferences.remove("noble_pending_invite")
            else:
                await self.preferences.set("noble_pending_invite", invite_code)
                await self.preferences.remove("noble_pending_shop_name")
        else:
            await self.preferences.remove("noble_pending_shop_name")
            await self.preferences.remove("noble_pending_invite")

        try:
            current = urlsplit(self.page.url or "")
            if not current.scheme or not current.netloc:
                raise RuntimeError("Open Noble POS from its web app URL before using Google sign-in.")
            callback_url = urlunsplit((current.scheme, current.netloc, current.path or "/", "", ""))
            verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(verifier.encode("ascii")).digest()
            ).rstrip(b"=").decode("ascii")
            await self.preferences.set("noble_google_pkce_verifier", verifier)
            query = urlencode({
                "provider": "google",
                "redirect_to": callback_url,
                "code_challenge": challenge,
                "code_challenge_method": "s256",
            })
            authorize_url = f"{self.api.url}/auth/v1/authorize?{query}"
            await ft.UrlLauncher().launch_url(
                authorize_url, web_only_window_name="_self"
            )
        except Exception as error:
            await self.preferences.remove("noble_google_pkce_verifier")
            log.warning("Could not start Google sign-in: %s", error)
            self.status = f"Could not start Google sign-in: {error}"
            self.render_auth()

    async def complete_google_callback(self):
        current = urlsplit(self.page.url or "")
        params = parse_qs(current.query)
        if current.fragment:
            fragment = current.fragment.split("?", 1)[-1]
            params.update(parse_qs(fragment))
        auth_code = (params.get("code") or [None])[0]
        oauth_error = (params.get("error_description") or params.get("error") or [None])[0]
        if not auth_code and not oauth_error:
            return False

        verifier = await self.preferences.get("noble_google_pkce_verifier")
        if oauth_error:
            await self.preferences.remove("noble_google_pkce_verifier")
            self.status = f"Google sign-in was cancelled or rejected: {oauth_error}"
            self.render_auth()
            return True
        if not verifier:
            self.status = "Google returned to the app, but the sign-in session expired. Please try again."
            self.render_auth()
            return True

        try:
            await self.preferences.remove("noble_google_pkce_verifier")
            await self.accept_session(await self.api.exchange_oauth_code(auth_code, verifier))
            await self.load_workspace()
        except Exception as error:
            log.warning("Google sign-in callback failed: %s", error)
            self.status = f"Google sign-in could not be completed: {error}"
            self.render_auth()
        return True

    async def sign_in(self, email, password):
        email = (email or "").strip().lower()
        if not email or not password:
            self.status = "Enter your email and password."
            self.render_auth()
            return
        try:
            await self.accept_session(await self.api.sign_in(email, password))
            self.status = ""
            await self.load_workspace()
        except Exception as error:
            detail = str(error)
            if "invalid login credentials" in detail.lower():
                self.status = (
                    "That email and password do not match an account in this Supabase project. "
                    "If you are new, choose ‘New here? Create an account’. If you just signed up, "
                    "confirm the email first if Supabase requires it."
                )
                log.warning("Sign-in rejected by Supabase: invalid credentials")
            else:
                self.status = f"Sign-in failed: {detail}"
                log.warning("Sign-in failed: %s", detail)
            self.render_auth()

    async def sign_up(self, email, password, full_name, shop_name, invite_code):
        email = (email or "").strip().lower()
        full_name = (full_name or "").strip()
        shop_name = (shop_name or "").strip()
        invite_code = (invite_code or "").strip()
        if not email or not password or not full_name:
            self.status = "Enter your email, password, and name."
            self.render_auth()
            return
        if bool(shop_name) == bool(invite_code):
            self.status = "Enter a shop name to create a shop, or an invite code to join an existing shop."
            self.render_auth()
            return
        if len(password) < 8:
            self.status = "Choose a password with at least 8 characters."
            self.render_auth()
            return
        try:
            if shop_name:
                await self.preferences.set("noble_pending_shop_name", shop_name)
                await self.preferences.remove("noble_pending_invite")
            else:
                await self.preferences.set("noble_pending_invite", invite_code)
                await self.preferences.remove("noble_pending_shop_name")
            result = await self.api.sign_up(email, password, full_name)
            if result.get("access_token"):
                await self.accept_session(result)
                await self.load_workspace()
            else:
                self.status = "Account created. Confirm the Supabase email, then sign in to complete setup."
                self.render_auth()
        except Exception as error:
            log.exception("Account creation failed")
            self.status = f"Account creation failed: {error}"
            self.render_auth()

    async def load_workspace(self):
        try:
            memberships = await self.api.list_memberships()
            if not memberships:
                pending_invite = await self.preferences.get("noble_pending_invite")
                if pending_invite:
                    membership = await self.api.redeem_invite(pending_invite)
                    if isinstance(membership, list):
                        membership = membership[0]
                    await self.preferences.remove("noble_pending_invite")
                    self.shop = await self.api.get_shop(membership["shop_id"])
                    self.role = membership.get("role", "cashier")
                else:
                    pending_name = await self.preferences.get("noble_pending_shop_name") or ""
                    self.page.clean()
                    self.page.add(screens.onboarding_screen("Create your shop profile.", pending_name, self.create_shop))
                    return
            else:
                membership = memberships[0]
                self.role = membership.get("role", "cashier")
                self.shop = await self.api.get_shop(membership["shop_id"])
                await self.preferences.remove("noble_pending_shop_name")
                await self.preferences.remove("noble_pending_invite")
            if not self.shop:
                raise RuntimeError("Your shop could not be loaded. Check that the Supabase schema and policies were installed.")
            self.status = ""
            await self.load_screen_data()
            self.render_workspace()
        except Exception as error:
            detail = str(error)
            log.warning("Loading shop data failed: %s", detail)
            if self.session:
                self.status = detail
                self.render_database_setup_error(detail)
            else:
                self.status = f"Could not load your shop: {detail}"
                self.render_auth()

    def render_database_setup_error(self, detail):
        message = (
            "Your account is signed in, but the database schema in Supabase is older than this app. "
            "Update the existing project before continuing. In Supabase open SQL Editor, paste the "
            "current full contents of src/core/schema.sql, and Run it."
        )
        self.page.clean()
        self.page.add(
            ft.SafeArea(
                content=ft.Column(
                    [
                        ft.Text("Database needs an update", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text(message),
                        ft.Text(f"Supabase returned: {detail}"),
                        ft.Button(content="Retry after database update", on_click=self.retry_workspace),
                        ft.TextButton(content="Sign out", on_click=self.sign_out),
                    ],
                    spacing=12,
                    expand=True,
                ),
                minimum_padding=ft.Padding.all(18),
                expand=True,
            )
        )

    async def retry_workspace(self):
        await self.load_workspace()

    async def create_shop(self, name, tax_rate):
        name = (name or "").strip()
        try:
            rate = float((tax_rate or "0").strip())
            if len(name) < 2 or not 0 <= rate <= 100:
                raise ValueError("Enter a shop name and a tax rate from 0 to 100.")
            self.shop = await self.api.create_shop(name, rate)
            self.role = "owner"
            await self.preferences.remove("noble_pending_shop_name")
        except Exception as error:
            log.warning("Shop creation failed: %s", error)
            self.status = f"Shop setup failed: {error}"
            self.page.clean()
            self.page.add(screens.onboarding_screen(self.status, name, self.create_shop))
            return

        try:
            await self.load_screen_data()
            self.status = "Shop created. Add inventory products to start selling."
        except Exception as error:
            log.warning("Shop created, but initial data load failed: %s", error)
            self.status = f"Your shop was created, but initial load failed: {error}"
        self.render_workspace()

    async def load_screen_data(self):
        if not self.shop:
            return
        shop_id = self.shop["id"]
        if self.selected_screen in ("Checkout", "Inventory"):
            self.inventory = await self.api.list_inventory(shop_id, self.search_query)
        if self.selected_screen in ("Checkout", "Customers"):
            self.customers = await self.api.list_customers(shop_id)
        if self.selected_screen in ("Reports",):
            self.sales = await self.api.list_sales(shop_id)
            self.expenses = await self.api.list_expenses(shop_id)
        if self.selected_screen == "Expenses":
            self.expenses = await self.api.list_expenses(shop_id)
        if self.selected_screen == "Team":
            self.team = await self.api.list_team(shop_id)

    def render_workspace(self):
        if self.shop:
            self.page.clean()
            self.page.add(screens.workspace_screen(self))

    async def refresh_workspace(self):
        try:
            await self.load_screen_data()
        except Exception as error:
            log.exception("Refreshing screen failed")
            self.status = f"Data refresh failed: {error}"
        self.render_workspace()

    async def navigate(self, target):
        self.selected_screen = target
        self.status = ""
        if target != "Inventory":
            self.editing_item = None
        await self.refresh_workspace()

    async def search_inventory(self, query):
        self.search_query = (query or "").strip()
        try:
            self.inventory = await self.api.list_inventory(self.shop["id"], self.search_query)
            
            # Auto-add to cart on exact barcode match (from scanner or manual scan)
            exact_match = next(
                (item for item in self.inventory if item.get("barcode") and item["barcode"] == self.search_query),
                None
            )
            if exact_match:
                await self.add_to_cart(exact_match["id"], "1")
                self.search_query = ""
                self.inventory = await self.api.list_inventory(self.shop["id"], "")
            else:
                self.status = ""
        except Exception as error:
            self.status = f"Search failed: {error}"
        self.render_workspace()

    async def add_to_cart(self, item_id, quantity_value):
        try:
            clean_qty = str(quantity_value or "1").replace(",", "").strip()
            quantity = int(clean_qty)
            if quantity <= 0:
                raise ValueError("Quantity must be a positive whole number.")
            item = next(row for row in self.inventory if row["id"] == item_id)
            existing = next((row for row in self.cart if row["id"] == item_id), None)
            desired = quantity + (existing["quantity"] if existing else 0)
            if desired > int(item["stock_qty"]):
                raise ValueError(f"Available stock for {item['name']}: {item['stock_qty']}.")
            if existing:
                existing["quantity"] = desired
            else:
                self.cart.append({
                    "id": item["id"], "name": item["name"],
                    "price": int(item["price"]), "quantity": quantity,
                })
            self.status = "Added to cart."
        except ValueError as ve:
            self.status = str(ve)
        except StopIteration:
            self.status = "Product is no longer available."
        except Exception as error:
            self.status = f"Could not add to cart: {error}"
        self.render_workspace()

    async def remove_from_cart(self, item_id):
        self.cart = [row for row in self.cart if row["id"] != item_id]
        self.status = "Cart updated."
        self.render_workspace()

    async def checkout(self, payment_type, paid_value, customer_id, discount_value, reference):
        try:
            clean_paid = str(paid_value or "0").replace(",", "").strip()
            clean_discount = str(discount_value or "0").replace(",", "").strip()
            paid = int(clean_paid or "0")
            discount = int(clean_discount or "0")
            if paid < 0 or discount < 0:
                raise ValueError("Payment and discount cannot be negative.")
            if payment_type == "CREDIT":
                paid = 0
            items = [{"id": row["id"], "quantity": row["quantity"]} for row in self.cart]
            result = await self.api.checkout(
                self.shop["id"], items, payment_type, paid, customer_id, discount, reference,
            )
            if isinstance(result, list):
                result = result[0]
            self.cart.clear()
            self.receipt_text = self.format_receipt(result, payment_type, reference)
            self.status = f"Sale complete • receipt {result.get('receipt_no', result.get('sale_id', ''))}"
            self.selected_screen = "Checkout"
            self.inventory = await self.api.list_inventory(self.shop["id"], self.search_query)
            self.customers = await self.api.list_customers(self.shop["id"])
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Checkout failed")
            self.status = f"Checkout failed: {error}"
        self.render_workspace()

    def format_receipt(self, result, payment_type, reference):
        shop_name = self.shop["name"]
        lines = [
            "========================================",
            shop_name.center(40),
            "Customer receipt".center(40),
            "========================================",
            f"Receipt: {result.get('receipt_no', '')}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Payment: {payment_type}",
        ]
        if reference:
            lines.append(f"Reference: {reference}")
        lines.extend([
            "----------------------------------------",
            f"Subtotal: {int(result.get('subtotal', 0)):,} {self.shop['currency']}",
            f"Discount: {int(result.get('discount', 0)):,} {self.shop['currency']}",
            f"Tax:      {int(result.get('tax', 0)):,} {self.shop['currency']}",
            f"TOTAL:    {int(result.get('total', 0)):,} {self.shop['currency']}",
            f"Paid:     {int(result.get('paid_amount', 0)):,} {self.shop['currency']}",
            f"Change:   {int(result.get('change_due', 0)):,} {self.shop['currency']}",
            "========================================",
            "Thank you for shopping with us!",
            "Not a fiscal EFD/VFD receipt.",
        ])
        return "\n".join(lines)

    async def save_receipt(self):
        try:
            result = await self.file_picker.save_file(
                dialog_title="Save customer receipt",
                file_name=f"Receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                src_bytes=self.receipt_text.encode("utf-8"),
            )
            self.status = "Receipt saved." if result else "Receipt save cancelled."
        except Exception as error:
            self.status = f"Could not save receipt: {error}"
        self.render_workspace()

    async def save_inventory(self, item_id, name, barcode, category, cost_value, price_value, reorder_value, opening_value):
        try:
            name = (name or "").strip()
            cost = int(str(cost_value or "0").replace(",", "").strip())
            price = int(str(price_value or "0").replace(",", "").strip())
            reorder = int(str(reorder_value or "0").replace(",", "").strip())
            opening = int(str(opening_value or "0").replace(",", "").strip())
            if not name or cost < 0 or price <= 0 or reorder < 0 or opening < 0:
                raise ValueError("Enter a name, non-negative cost/stock/alert, and a positive selling price.")
            values = {
                "shop_id": self.shop["id"], "name": name,
                "barcode": (barcode or "").strip() or None,
                "category": (category or "General").strip() or "General",
                "cost_price": cost, "price": price, "reorder_level": reorder,
                "active": True,
            }
            if item_id:
                values["id"] = item_id
                await self.api.save_inventory_item(values)
                self.status = f"Updated {name}. Use stock adjustment to change quantity."
            else:
                values["stock_qty"] = opening
                await self.api.save_inventory_item(values)
                self.status = f"Added {name} to inventory."
            self.editing_item = None
            self.inventory = await self.api.list_inventory(self.shop["id"], self.search_query)
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Saving inventory failed")
            self.status = f"Could not save product: {error}"
        self.render_workspace()

    def edit_inventory(self, item):
        self.editing_item = dict(item)
        self.status = f"Editing {item['name']}; stock quantity remains unchanged."
        self.render_workspace()

    async def adjust_stock(self, item_id, delta_value, note):
        try:
            if not item_id:
                raise ValueError("Select a product first.")
            delta = int(str(delta_value or "0").replace(",", "").strip())
            await self.api.adjust_inventory_stock(self.shop["id"], item_id, delta, (note or "").strip())
            self.status = "Stock adjustment recorded."
            self.inventory = await self.api.list_inventory(self.shop["id"], self.search_query)
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Stock adjustment failed")
            self.status = f"Stock adjustment failed: {error}"
        self.render_workspace()

    async def save_customer(self, name, phone, credit_limit, due_date):
        try:
            name = (name or "").strip()
            limit = int(str(credit_limit or "0").replace(",", "").strip())
            if not name or limit < 0:
                raise ValueError("Enter a name and a non-negative credit limit.")
            await self.api.save_customer({
                "shop_id": self.shop["id"], "name": name,
                "phone": (phone or "").strip(), "credit_limit": limit,
                "due_date": (due_date or "").strip() or None, "active": True,
            })
            self.status = f"Registered {name}."
            self.customers = await self.api.list_customers(self.shop["id"])
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Saving customer failed")
            self.status = f"Could not register customer: {error}"
        self.render_workspace()

    async def record_debt_payment(self, customer_id, amount_value, payment_type, reference):
        try:
            if not customer_id:
                raise ValueError("Select a customer.")
            amount = int(str(amount_value or "0").replace(",", "").strip())
            await self.api.record_debt_payment(
                self.shop["id"], customer_id, amount, payment_type or "CASH", (reference or "").strip(),
            )
            self.status = "Debt payment recorded."
            self.customers = await self.api.list_customers(self.shop["id"])
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Debt payment failed")
            self.status = f"Could not record payment: {error}"
        self.render_workspace()

    async def save_expense(self, title, category, amount_value, description):
        try:
            amount = int(str(amount_value or "0").replace(",", "").strip())
            title = (title or "").strip()
            if not title or amount <= 0:
                raise ValueError("Enter an expense title and a positive amount.")
            await self.api.add_expense({
                "shop_id": self.shop["id"], "user_id": self.api.user_id,
                "title": title, "category": (category or "Other").strip() or "Other",
                "amount": amount, "description": (description or "").strip(),
            })
            self.status = "Expense recorded."
            self.expenses = await self.api.list_expenses(self.shop["id"])
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Saving expense failed")
            self.status = f"Could not record expense: {error}"
        self.render_workspace()

    async def void_sale(self, sale_id, reason):
        reason_clean = (reason or "").strip()
        if len(reason_clean) < 3:
            self.status = "Provide a reason for voiding (at least 3 characters)."
            self.render_workspace()
            return
        try:
            await self.api.void_sale(self.shop["id"], sale_id, reason_clean)
            self.status = "Sale voided and stock restored."
            self.sales = await self.api.list_sales(self.shop["id"])
            self.inventory = await self.api.list_inventory(self.shop["id"])
            self.customers = await self.api.list_customers(self.shop["id"])
        except Exception as error:
            log.exception("Sale void failed")
            self.status = f"Could not void sale: {error}"
        self.render_workspace()

    async def create_invite(self, role):
        try:
            self.invite_code = await self.api.create_invite(self.shop["id"], role or "cashier")
            self.status = "Invitation created. Share the code privately; it expires in 7 days."
            self.team = await self.api.list_team(self.shop["id"])
        except Exception as error:
            log.exception("Staff invite failed")
            self.status = f"Could not create invitation: {error}"
        self.render_workspace()

    async def save_settings(self, name, tax_value):
        try:
            if self.role != "owner":
                raise ValueError("Only the owner can change shop settings.")
            rate = float((tax_value or "").strip())
            name = (name or "").strip()
            if len(name) < 2 or not 0 <= rate <= 100:
                raise ValueError("Enter a shop name and tax rate from 0 to 100.")
            await self.api.update_shop(self.shop["id"], {"name": name, "tax_rate": rate})
            self.shop = await self.api.get_shop(self.shop["id"])
            self.status = "Settings saved."
        except ValueError as ve:
            self.status = str(ve)
        except Exception as error:
            log.exception("Saving settings failed")
            self.status = f"Could not save settings: {error}"
        self.render_workspace()

    async def sign_out(self):
        try:
            if self.session:
                await self.api.sign_out()
        except Exception as error:
            log.info("Remote sign-out did not complete: %s", error)
        await self.clear_session()
        self.cart.clear()
        self.status = ""
        self.render_auth()