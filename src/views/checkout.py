import flet as ft


def _open_payment_dialog(page, shop, customers, cart, on_checkout):
    subtotal = sum(int(row["price"]) * int(row["quantity"]) for row in cart)
    payment = ft.Dropdown(
        label="Payment method",
        value="CASH",
        options=[ft.DropdownOption(text=value) for value in ("CASH", "MOBILE_MONEY", "CARD", "CREDIT")],
    )
    customer = ft.Dropdown(
        label="Customer (required for credit)",
        options=[
            ft.DropdownOption(text=f"{row['id']} :: {row['name']} (balance {int(row['balance']):,})")
            for row in customers
        ],
    )
    discount = ft.TextField(label=f"Discount ({shop['currency']})", value="0")
    paid = ft.TextField(label=f"Amount received ({shop['currency']}; credit = 0)", value="0")
    reference = ft.TextField(label="Mobile money / card reference (optional)")
    total_label = ft.Text(weight=ft.FontWeight.BOLD, size=18)
    tax_label = ft.Text()

    def calculate_totals():
        try:
            discount_amount = max(0, int((discount.value or "0").replace(",", "").strip()))
        except ValueError:
            discount_amount = 0
        discount_amount = min(discount_amount, subtotal)
        taxable = subtotal - discount_amount
        tax = round(taxable * float(shop.get("tax_rate") or 0) / 100)
        total = taxable + tax
        return discount_amount, tax, total

    def update_totals():
        discount_amount, tax, total = calculate_totals()
        tax_label.value = f"Subtotal {subtotal:,}  ·  Discount {discount_amount:,}  ·  Tax {tax:,} {shop['currency']}"
        total_label.value = f"Total  {total:,} {shop['currency']}"
        page.update()

    update_totals()
    discount.on_change = update_totals

    async def complete():
        selection = customer.value or ""
        customer_id = selection.split(" :: ", 1)[0] if " :: " in selection else None
        page.pop_dialog()
        await on_checkout(
            payment.value or "CASH", paid.value, customer_id,
            discount.value or "0", reference.value or "",
        )

    def cancel():
        page.pop_dialog()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Payment details"),
            content=ft.Column(
                [
                    tax_label,
                    total_label,
                    payment,
                    customer,
                    discount,
                    paid,
                    reference,
                ],
                tight=True,
                spacing=12,
            ),
            scrollable=True,
            actions=[
                ft.TextButton(content="Back", on_click=cancel),
                ft.Button(content="Complete sale", on_click=complete),
            ],
        )
    )


def _open_receipt_dialog(page, receipt_text, on_save_receipt):
    async def save():
        page.pop_dialog()
        await on_save_receipt()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Latest receipt"),
            content=ft.Text(receipt_text, selectable=True, font_family="monospace"),
            scrollable=True,
            actions=[
                ft.TextButton(content="Close", on_click=page.pop_dialog),
                ft.Button(content="Save as text file", on_click=save),
            ],
        )
    )


def view(page, shop, inventory, customers, cart, status, receipt_text, on_search, on_add, on_remove, on_checkout, on_save_receipt, search_query=""):
    search = ft.TextField(label="Search item or scan barcode, then press Enter", value=search_query)
    quantity = ft.TextField(label="Quantity to add", value="1", width=140)
    subtotal = sum(int(row["price"]) * int(row["quantity"]) for row in cart)

    async def search_submitted(event):
        await on_search(event.control.value or "")

    def open_payment():
        _open_payment_dialog(page, shop, customers, cart, on_checkout)

    def open_receipt():
        _open_receipt_dialog(page, receipt_text, on_save_receipt)

    def add_handler(item_id):
        async def add():
            await on_add(item_id, quantity.value)
        return add

    def remove_handler(item_id):
        async def remove():
            await on_remove(item_id)
        return remove

    products = []
    for item in inventory:
        products.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(item["name"], weight=ft.FontWeight.BOLD),
                                ft.Text(f"{int(item['price']):,} {shop['currency']}  ·  Stock {item['stock_qty']}"),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Button(content="Add", on_click=add_handler(item["id"]), disabled=int(item["stock_qty"]) <= 0),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                bgcolor=ft.Colors.WHITE,
                border_radius=10,
            )
        )

    if products:
        product_panel = ft.Container(
            content=ft.Column(products, spacing=5, scroll=ft.ScrollMode.AUTO),
            height=min(230, max(80, len(products) * 62)),
            padding=ft.Padding.all(8),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=12,
        )
    else:
        product_panel = ft.Container(
            content=ft.Text("No products yet. Add your first item in Inventory."),
            padding=ft.Padding.all(16),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=12,
        )

    if cart:
        cart_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(f"{row['name']} × {row['quantity']}", expand=True),
                        ft.Text(f"{row['price'] * row['quantity']:,} {shop['currency']}"),
                        ft.TextButton("Remove", on_click=remove_handler(row["id"])),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
                for row in cart
            ],
            spacing=4,
        )
    else:
        cart_content = ft.Text("Your cart is empty. Add a product above.")

    return ft.Column(
        [
            ft.Text("Checkout", size=22, weight=ft.FontWeight.BOLD),
            ft.Text(status, visible=bool(status)),
            search,
            quantity,
            product_panel,
            ft.Text(f"Current sale · {len(cart)} item types", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=cart_content,
                padding=ft.Padding.all(12),
                bgcolor=ft.Colors.WHITE,
                border=ft.Border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=12,
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Subtotal  {subtotal:,} {shop['currency']}"),
                        ft.Text("Taxes and discounts confirmed in payment details."),
                    ],
                    spacing=4,
                ),
                padding=ft.Padding.all(14),
                bgcolor=ft.Colors.BLUE_GREY_50,
                border_radius=12,
            ),
            ft.Button(
                content="Payment details",
                on_click=open_payment,
                disabled=not bool(cart),
            ),
            *(
                [ft.OutlinedButton(content="View latest receipt", on_click=open_receipt)]
                if receipt_text else []
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=10,
    )
