import flet as ft


def view(shop, sales, expenses, role, status, on_void):
    reason = ft.TextField(label="Reason required to void a sale")
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

        def void_handler(sale_id):
            async def void():
                await on_void(sale_id, reason.value)
            return void

        action = ft.TextButton(
            "Void sale",
            on_click=void_handler(sale["id"]),
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
            ft.Text(status),
            ft.Text(f"Completed sales in latest {len(sales)} records: {revenue:,} {shop['currency']}"),
            ft.Text(f"Estimated gross profit: {profit:,} {shop['currency']} • expenses in latest 200: {spend:,} {shop['currency']}"),
            ft.Text("Sales totals by method: " + (" • ".join(f"{key}: {amount:,}" for key, amount in sorted(methods.items())) or "No sales yet")),
            ft.Divider(),
            ft.Text("Void a completed sale (owner/manager only)", weight=ft.FontWeight.BOLD),
            reason,
            ft.Column(rows, scroll=ft.ScrollMode.AUTO, expand=True),
        ],
        expand=True,
    )
