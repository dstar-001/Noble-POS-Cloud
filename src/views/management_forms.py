import flet as ft


def _show_form(page, title, controls, action_label, on_submit, disabled=False):
    async def submit():
        page.pop_dialog()
        await on_submit()

    def cancel():
        page.pop_dialog()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Column(controls, tight=True, spacing=12),
            scrollable=True,
            actions=[
                ft.TextButton(content="Cancel", on_click=cancel),
                ft.Button(content=action_label, on_click=submit, disabled=disabled),
            ],
        )
    )


def inventory_form(page, shop, item, on_save, can_manage):
    editing = item or {}
    name = ft.TextField(label="Product name", value=editing.get("name", ""))
    barcode = ft.TextField(label="Barcode", value=editing.get("barcode", ""))
    category = ft.TextField(label="Category", value=editing.get("category", "General"))
    cost = ft.TextField(label=f"Unit cost ({shop['currency']})", value=str(editing.get("cost_price", "")))
    price = ft.TextField(label=f"Selling price ({shop['currency']})", value=str(editing.get("price", "")))
    reorder = ft.TextField(label="Low-stock alert at", value=str(editing.get("reorder_level", 0)))
    opening = ft.TextField(label="Opening stock", value="0", visible=not bool(item))

    async def save():
        await on_save(
            editing.get("id"), name.value, barcode.value, category.value,
            cost.value, price.value, reorder.value, opening.value,
        )

    _show_form(
        page,
        "Edit product" if item else "Add product",
        [name, barcode, category, cost, price, reorder, opening],
        "Save product",
        save,
        disabled=not can_manage,
    )


def stock_adjustment_form(page, inventory, on_adjust, can_manage):
    options = [
        ft.DropdownOption(text=f"{item['id']} :: {item['name']} (stock {item['stock_qty']})")
        for item in inventory
    ]
    product = ft.Dropdown(label="Product", options=options, value=options[0].text if options else None)
    quantity = ft.TextField(label="Quantity change (+ receive / - correction)")
    reason = ft.TextField(label="Reason (delivery, count, damage)")

    async def adjust():
        selection = product.value or ""
        product_id = selection.split(" :: ", 1)[0] if " :: " in selection else None
        await on_adjust(product_id, quantity.value, reason.value)

    _show_form(
        page, "Receive or correct stock", [product, quantity, reason],
        "Apply adjustment", adjust,
        disabled=not can_manage or not bool(inventory),
    )


def customer_form(page, shop, on_save, can_manage):
    name = ft.TextField(label="Customer name")
    phone = ft.TextField(label="Phone number")
    limit = ft.TextField(label=f"Credit limit ({shop['currency']})", value="50000")
    due_date = ft.TextField(label="Due date (YYYY-MM-DD, optional)")

    async def save():
        await on_save(name.value, phone.value, limit.value, due_date.value)

    _show_form(page, "Add customer", [name, phone, limit, due_date], "Save customer", save, not can_manage)


def debt_payment_form(page, shop, customers, on_payment, can_manage, selected_customer_id=None):
    options = [
        ft.DropdownOption(text=f"{row['id']} :: {row['name']} (balance {int(row['balance']):,})")
        for row in customers
    ]
    selected = next(
        (option.text for option in options if selected_customer_id and option.text.startswith(f"{selected_customer_id} :: ")),
        options[0].text if options else None,
    )
    customer = ft.Dropdown(label="Customer account", options=options, value=selected)
    amount = ft.TextField(label=f"Payment amount ({shop['currency']})")
    payment_type = ft.Dropdown(
        label="Payment method",
        value="CASH",
        options=[ft.DropdownOption(text=kind) for kind in ("CASH", "MOBILE_MONEY", "CARD")],
    )
    reference = ft.TextField(label="Payment reference (optional)")

    async def record():
        selection = customer.value or ""
        customer_id = selection.split(" :: ", 1)[0] if " :: " in selection else None
        await on_payment(customer_id, amount.value, payment_type.value, reference.value)

    _show_form(
        page, "Record customer payment", [customer, amount, payment_type, reference],
        "Record payment", record,
        disabled=not can_manage or not bool(customers),
    )


def expense_form(page, shop, on_save, can_manage):
    title = ft.TextField(label="Expense title")
    category = ft.Dropdown(
        label="Category",
        value="Other",
        options=[
            ft.DropdownOption(text=value)
            for value in ("Rent", "Utilities", "Salaries", "Transport", "Stock loss", "Maintenance", "Other")
        ],
    )
    amount = ft.TextField(label=f"Amount ({shop['currency']})")
    description = ft.TextField(label="Description (optional)", multiline=True, min_lines=2, max_lines=4)

    async def save():
        await on_save(title.value, category.value, amount.value, description.value)

    _show_form(page, "Record expense", [title, category, amount, description], "Save expense", save, not can_manage)


def invite_form(page, on_create_invite, can_manage):
    role = ft.Dropdown(
        label="Invite role",
        value="cashier",
        options=[ft.DropdownOption(text=value) for value in ("cashier", "manager")],
    )

    async def create():
        await on_create_invite(role.value)

    _show_form(page, "Invite a staff member", [
        ft.Text("The single-use code expires after 7 days. Share it privately."),
        role,
    ], "Generate invite", create, not can_manage)
