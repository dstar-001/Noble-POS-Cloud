import httpx2 as httpx


class SupabaseClient:
    """Async Supabase Auth, PostgREST and RPC client."""

    def __init__(self, url: str, anon_key: str):
        self.url = url.rstrip("/")
        self.anon_key = anon_key.strip()
        self.access_token = None
        self.refresh_token = None
        self.user_id = None

    @property
    def configured(self):
        return bool(self.url and self.anon_key)

    async def _send(self, method, path, *, body=None, params=None, bearer=None, prefer=None):
        if not self.configured:
            raise RuntimeError("Supabase is not configured. Set the project URL and public key in src/config.py.")
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        if prefer:
            headers["Prefer"] = prefer
        async with httpx.AsyncClient(timeout=25.0) as client:
            return await client.request(
                method, f"{self.url}{path}", headers=headers, params=params, json=body
            )

    @staticmethod
    def _decode(response):
        if response.is_error:
            try:
                payload = response.json()
                detail = (
                    payload.get("message")
                    or payload.get("msg")
                    or payload.get("error_description")
                    or str(payload)
                )
            except Exception:
                detail = response.text or f"HTTP {response.status_code}"
            raise RuntimeError(detail)
        if not response.content:
            return None
        return response.json()

    async def request(self, method, path, *, body=None, params=None, prefer=None, authenticated=True):
        bearer = self.access_token if authenticated else None
        response = await self._send(
            method, path, body=body, params=params, bearer=bearer, prefer=prefer
        )
        return self._decode(response)

    async def rpc(self, name, args):
        return await self.request("POST", f"/rest/v1/rpc/{name}", body=args)

    async def sign_in(self, email, password):
        return await self.request(
            "POST", "/auth/v1/token", params={"grant_type": "password"},
            body={"email": email, "password": password}, authenticated=False,
        )

    async def sign_up(self, email, password, full_name):
        return await self.request(
            "POST", "/auth/v1/signup",
            body={"email": email, "password": password, "data": {"full_name": full_name}},
            authenticated=False,
        )

    async def exchange_oauth_code(self, auth_code, code_verifier):
        return await self.request(
            "POST", "/auth/v1/token", params={"grant_type": "pkce"},
            body={"auth_code": auth_code, "code_verifier": code_verifier},
            authenticated=False,
        )

    async def get_user(self, token=None):
        if token:
            response = await self._send("GET", "/auth/v1/user", bearer=token)
            return self._decode(response)
        return await self.request("GET", "/auth/v1/user")

    async def refresh_session(self, refresh_token):
        return await self.request(
            "POST", "/auth/v1/token", params={"grant_type": "refresh_token"},
            body={"refresh_token": refresh_token}, authenticated=False,
        )

    async def sign_out(self):
        try:
            await self.request("POST", "/auth/v1/logout")
        finally:
            self.access_token = None
            self.refresh_token = None
            self.user_id = None

    async def list_memberships(self):
        return await self.request(
            "GET", "/rest/v1/shop_members",
            params={"select": "shop_id,role,shops(id,name,currency,tax_rate,subscription_status)", "user_id": f"eq.{self.user_id}"},
        )

    async def create_shop(self, name, tax_rate):
        rows = await self.request(
            "POST", "/rest/v1/shops",
            body={"name": name, "created_by": self.user_id, "tax_rate": tax_rate},
            prefer="return=representation",
        )
        shop = rows[0]
        await self.request(
            "POST", "/rest/v1/shop_members",
            body={"shop_id": shop["id"], "user_id": self.user_id, "role": "owner"},
            prefer="return=minimal",
        )
        return shop

    async def redeem_invite(self, invite_code):
        return await self.rpc("redeem_shop_invite", {"p_code": invite_code})

    async def create_invite(self, shop_id, role):
        return await self.rpc("create_shop_invite", {"p_shop_id": shop_id, "p_role": role})

    async def list_team(self, shop_id):
        return await self.request(
            "GET", "/rest/v1/shop_members",
            params={"select": "user_id,role,created_at", "shop_id": f"eq.{shop_id}", "order": "created_at.asc"},
        )

    async def adjust_inventory_stock(self, shop_id, inventory_id, delta, note):
        return await self.rpc("adjust_inventory_stock", {
            "p_shop_id": shop_id, "p_inventory_id": inventory_id,
            "p_delta": delta, "p_note": note,
        })

    async def list_inventory(self, shop_id, query=""):
        params = {
            "select": "id,name,barcode,category,cost_price,price,stock_qty,reorder_level",
            "shop_id": f"eq.{shop_id}", "order": "name.asc", "limit": "500",
        }
        if query.strip():
            term = query.strip().replace(",", " ").replace("(", " ").replace(")", " ")
            params["or"] = f"(name.ilike.*{term}*,barcode.ilike.*{term}*)"
        return await self.request("GET", "/rest/v1/inventory", params=params)

    async def save_inventory_item(self, item):
        if item.get("id"):
            item_id = item.pop("id")
            await self.request(
                "PATCH", "/rest/v1/inventory", params={"id": f"eq.{item_id}"},
                body=item, prefer="return=minimal",
            )
            return item_id
        rows = await self.request(
            "POST", "/rest/v1/inventory", body=item, prefer="return=representation"
        )
        return rows[0]["id"]

    async def checkout(self, shop_id, items, payment_type, paid_amount, customer_id=None, discount=0, reference=""):
        return await self.rpc("checkout_sale", {
            "p_shop_id": shop_id,
            "p_items": items,
            "p_payment_type": payment_type,
            "p_paid_amount": paid_amount,
            "p_customer_id": customer_id,
            "p_discount": discount,
            "p_payment_reference": reference,
        })

    async def list_sales(self, shop_id, limit=200):
        return await self.request(
            "GET", "/rest/v1/sales",
            params={
                "select": "id,receipt_no,subtotal,discount,tax,total,paid_amount,change_due,payment_type,payment_reference,status,created_at,customers(name)",
                "shop_id": f"eq.{shop_id}", "order": "created_at.desc", "limit": str(limit),
            },
        )

    async def void_sale(self, shop_id, sale_id, reason):
        return await self.rpc("void_sale", {"p_shop_id": shop_id, "p_sale_id": sale_id, "p_reason": reason})

    async def list_sale_items(self, sale_id):
        return await self.request(
            "GET", "/rest/v1/sale_items",
            params={"select": "item_name,quantity,unit_price,line_total", "sale_id": f"eq.{sale_id}", "order": "created_at.asc"},
        )

    async def list_customers(self, shop_id, query=""):
        params = {
            "select": "id,name,phone,balance,credit_limit,due_date",
            "shop_id": f"eq.{shop_id}", "order": "name.asc", "limit": "500",
        }
        if query.strip():
            term = query.strip().replace(",", " ").replace("(", " ").replace(")", " ")
            params["or"] = f"(name.ilike.*{term}*,phone.ilike.*{term}*)"
        return await self.request("GET", "/rest/v1/customers", params=params)

    async def save_customer(self, customer):
        if customer.get("id"):
            customer_id = customer.pop("id")
            await self.request(
                "PATCH", "/rest/v1/customers", params={"id": f"eq.{customer_id}"},
                body=customer, prefer="return=minimal",
            )
            return customer_id
        rows = await self.request(
            "POST", "/rest/v1/customers", body=customer, prefer="return=representation"
        )
        return rows[0]["id"]

    async def record_debt_payment(self, shop_id, customer_id, amount, reference=""):
        return await self.rpc("record_debt_payment", {
            "p_shop_id": shop_id, "p_customer_id": customer_id,
            "p_amount": amount, "p_reference": reference,
        })

    async def list_expenses(self, shop_id, limit=200):
        return await self.request(
            "GET", "/rest/v1/expenses",
            params={
                "select": "id,title,category,amount,description,created_at",
                "shop_id": f"eq.{shop_id}", "order": "created_at.desc", "limit": str(limit),
            },
        )

    async def add_expense(self, expense):
        return await self.request("POST", "/rest/v1/expenses", body=expense, prefer="return=minimal")

    async def update_shop(self, shop_id, values):
        await self.request(
            "PATCH", "/rest/v1/shops", params={"id": f"eq.{shop_id}"},
            body=values, prefer="return=minimal",
        )

    async def get_shop(self, shop_id):
        rows = await self.request(
            "GET", "/rest/v1/shops",
            params={"select": "id,name,currency,tax_rate,subscription_status", "id": f"eq.{shop_id}", "limit": "1"},
        )
        return rows[0] if rows else None
