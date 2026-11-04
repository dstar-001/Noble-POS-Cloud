import flet as ft


def view(shop, sales, expenses, role, status, on_void):
    active_sales = [sale for sale in sales if sale.get("status") == "completed"]
    revenue = sum(int(sale["total"]) for sale in active_sales)
    profit = sum(int(sale.get("profit") or 0) for sale in active_sales)
    spend = sum(int(row["amount"]) for row in expenses)
    methods = {}
    for sale in active_sales:
        kind = sale.get("payment_type", "UNKNOWN")
        methods[kind] = methods.get(kind, 0) + int(sale["total"])

    rows = []
    for sale in sales:
        customer = (sale.get("customers") or {}).get("name") or "Walk-in"

        def open_void_dialog(sale_id, receipt_no):
            reason_input = ft.TextField(
                label="Reason for voiding (min 3 chars)",
                hint_text="e.g., Customer returned item / Cashier mistake",
                autofocus=True,
            )

            async def confirm_void(e):
                val = (reason_input.value or "").strip()
                if len(val) < 3:
                    reason_input.error_text = "Please enter at least 3 characters."
                    reason_input.update()
                    return
                e.control.page.pop_dialog()
                await on_void(sale_id, val)

            def show(page):
                page.show_dialog(
                    ft.AlertDialog(
                        title=ft.Text(f"Void Sale {receipt_no}"),
                        content=ft.Column(
                            [
                                ft.Text("This will restore inventory stock and update report figures."),
                                reason_input,
                            ],
                            tight=True,
                            spacing=10,
                        ),
                        actions=[
                            ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                            ft.Button("Confirm Void", on_click=confirm_void),
                        ],
                    )
                )

            return show

        def void_click_handler(s_id, r_no):
            async def handler(e):
                open_void_dialog(s_id, r_no)(e.page)
            return handler

        action = ft.TextButton(
            "Void sale",
            on_click=void_click_handler(sale["id"], sale.get("receipt_no") or sale["id"][:8]),
            visible=role in ("owner", "manager") and sale.get("status") == "completed",
        )
        rows.append(
            ft.Row(
                [
                    ft.Text(
                        f"{sale.get('receipt_no') or sale['id'][:8]} • {sale['created_at'][:19].replace('T',' ')} • "
                        f"{customer} • {sale['payment_type']} • {int(sale['total']):,} {shop['currency']} • {sale['status']}",
                        expand=True,
                    ),
                    action,
                ],
            )
        )

    return ft.Column(
        [
            ft.Text("Sales and reports", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(status, visible=bool(status)),
            ft.Text(f"Completed sales in latest {len(sales)} records: {revenue:,} {shop['currency']}"),
            ft.Text(f"Estimated gross profit: {profit:,} {shop['currency']} • expenses in latest 200: {spend:,} {shop['currency']}"),
            ft.Text("Sales totals by method: " + (" • ".join(f"{key}: {amount:,}" for key, amount in sorted(methods.items())) or "No sales yet")),
            ft.Divider(),
            ft.Column(rows, scroll=ft.ScrollMode.AUTO, expand=True),
        ],
        expand=True,
    )