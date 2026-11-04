import flet as ft

from views import management_forms


def _status(value):
    return ft.Container(
        content=ft.Text(value),
        visible=bool(value),
    )


def inventory_view(page, shop, inventory, role, status, editing, on_save, on_edit, on_adjust, on_search):
    can_manage = role in ("owner", "manager")
    filter_field = ft.TextField(label="Find by product name or barcode")

    async def search_submitted(event):
        await on_search(event.control.value or "")

    filter_field.on_submit = search_submitted

    def add_product():
        management_forms.inventory_form(page, shop, None, on_save, can_manage)

    def adjust_stock():
        management_forms.stock_adjustment_form(page, inventory, on_adjust, can_manage)

    def edit_product(item):
        def open_form():
            management_forms.inventory_form(page, shop, item, on_save, can_manage)
        return open_form

    rows = []
    for item in inventory:
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item["name"], weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"{int(item['price']):,} {shop['currency']}  ·  Stock {item['stock_qty']}  ·  "
                                    f"Cost {int(item['cost_price']):,}  ·  Alert at {item.get('reorder_level', 0)}"
                                ),
                                ft.Text(f"Barcode: {item.get('barcode') or 'Not set'}  ·  {item.get('category', 'General')}")
                            ],
                            spacing=3,
                            expand=True,
                        ),
                        ft.TextButton("Edit", on_click=edit_product(item), disabled=not can_manage),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.all(12),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=12,
            )
        )

    if not rows:
        rows = [ft.Text("No products yet. Add your first product to start selling.")]

    return ft.Column(
        [
            ft.Text("Inventory", size=22, weight=ft.FontWeight.BOLD),
            _status(status),
            ft.Row(
                [
                    ft.Button(content="Add product", on_click=add_product, disabled=not can_manage),
                    ft.OutlinedButton(content="Stock adjustment", on_click=adjust_stock, disabled=not can_manage),
                ],
                wrap=True,
            ),
            filter_field,
            ft.Column(rows, spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
        ],
        expand=True,
        spacing=10,
    )


def customers_view(page, shop, customers, role, status, on_save, on_payment):
    can_manage = role in ("owner", "manager")

    def add_customer():
        management_forms.customer_form(page, shop, on_save, can_manage)

    def collect_payment(customer_id=None):
        def open_form():
            management_forms.debt_payment_form(
                page, shop, customers, on_payment, can_manage, customer_id,
            )
        return open_form

    rows = []
    for row in customers:
        rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(row["name"], weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    f"{row.get('phone') or 'No phone'}  ·  Balance {int(row['balance']):,} / "
                                    f"Limit {int(row['credit_limit']):,} {shop['currency']}  ·  "
                                    f"Due {row.get('due_date') or '—'}"
                                ),
                            ],
                            spacing=3,
                            expand=True,
                        ),
                        ft.TextButton("Payment", on_click=collect_payment(row["id"]), disabled=not can_manage),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.all(12),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=12,
            )
        )

    if not rows:
        rows = [ft.Text("No customers yet. Add a customer to manage credit accounts.")]

    return ft.Column(
        [
            ft.Text("Customers", size=22, weight=ft.FontWeight.BOLD),
            _status(status),
            ft.Row(
                [
                    ft.Button(content="Add customer", on_click=add_customer, disabled=not can_manage),
                    ft.OutlinedButton(content="Record payment", on_click=collect_payment(), disabled=not can_manage or not bool(customers)),
                ],
                wrap=True,
            ),
            ft.Column(rows, spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
        ],
        expand=True,
        spacing=10,
    )


def expenses_view(page, shop, expenses, role, status, on_save):
    can_manage = role in ("owner", "manager")

    def add_expense():
        management_forms.expense_form(page, shop, on_save, can_manage)

    rows = [
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(row["title"], weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{row['created_at'][:19].replace('T', ' ')}  ·  {row['category']}  ·  "
                        f"{int(row['amount']):,} {shop['currency']}"
                    ),
                    ft.Text(row.get("description") or ""),
                ],
                spacing=3,
            ),
            padding=ft.Padding.all(12),
            bgcolor=ft.Colors.WHITE,
            border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
            border_radius=12,
        )
        for row in expenses
    ]
    if not rows:
        rows = [ft.Text("No expenses recorded yet.")]

    return ft.Column(
        [
            ft.Text("Expenses", size=22, weight=ft.FontWeight.BOLD),
            _status(status),
            ft.Button(content="Record expense", on_click=add_expense, disabled=not can_manage),
            ft.Column(rows, spacing=8, expand=True, scroll=ft.ScrollMode.AUTO),
        ],
        expand=True,
        spacing=10,
    )


def team_view(page, role, invite_code, status, on_create_invite):
    can_manage = role in ("owner", "manager")

    def invite():
        management_forms.invite_form(page, on_create_invite, can_manage)

    return ft.Column(
        [
            ft.Text("Team access", size=22, weight=ft.FontWeight.BOLD),
            _status(status),
            ft.Text("Invite staff using a private, single-use code that expires after 7 days."),
            ft.Button(content="Create staff invite", on_click=invite, disabled=not can_manage),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Latest invite", weight=ft.FontWeight.BOLD),
                        ft.Text(invite_code or "No invite generated yet.", selectable=True),
                    ],
                    spacing=6,
                ),
                padding=ft.Padding.all(14),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=12,
            ),
            ft.Text("Cashiers sell and view customers. Managers can also manage stock and expenses. Owners manage shop settings and can void sales."),
        ],
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )


def settings_view(shop, role, status, on_save):
    name = ft.TextField(label="Shop name", value=shop["name"], read_only=role != "owner")
    tax = ft.TextField(label="Tax rate (%)", value=str(shop.get("tax_rate") or 0), read_only=role != "owner")

    async def save():
        await on_save(name.value, tax.value)

    return ft.Column(
        [
            ft.Text("Shop settings", size=22, weight=ft.FontWeight.BOLD),
            _status(status),
            name,
            tax,
            ft.Button(content="Save settings", on_click=save, disabled=role != "owner"),
            ft.Text(f"Currency: {shop['currency']} (Tanzanian shillings). Fiscal EFD/VFD integration is not configured."),
            ft.Text(f"Subscription status: {shop['subscription_status']}. Subscription activation and suspension are admin-managed manually."),
        ],
        expand=True,
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
    )
