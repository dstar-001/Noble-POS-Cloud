import flet as ft

from views import auth, checkout, management, reports


MOBILE_DESTINATIONS = ["Checkout", "Inventory", "Customers", "More"]
DESTINATION_ICONS = [ft.Icons.SHOPPING_BAG, ft.Icons.INVENTORY_2, ft.Icons.PEOPLE, ft.Icons.MORE_VERT]
MORE_SCREENS = ["Expenses", "Reports", "Team", "Settings"]


def auth_screen(page, status, on_login, on_signup, on_google, configured):
    width = page.width or 390
    card_width = min(width - 32, 440)
    return ft.SafeArea(
        content=ft.Row(
            [
                ft.Container(
                    width=card_width,
                    padding=ft.Padding.symmetric(horizontal=24, vertical=26),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=20,
                    shadow=ft.BoxShadow(
                        blur_radius=24,
                        spread_radius=1,
                        color=ft.Colors.with_opacity(0.08, ft.Colors.BLUE_GREY_900),
                        offset=ft.Offset(0, 8),
                    ),
                    content=auth.auth_screen(status, on_login, on_signup, on_google, configured),
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        ),
        minimum_padding=ft.Padding.all(12),
        expand=True,
    )


def onboarding_screen(status, default_name, on_create):
    return auth.onboarding_screen(status, default_name, on_create)


def workspace_screen(app):
    page = app.page
    is_mobile = (page.width or 1000) < 700

    def nav_handler(target):
        async def navigate():
            await app.navigate(target)
        return navigate

    async def change_destination(event):
        target = MOBILE_DESTINATIONS[event.control.selected_index]
        await app.navigate(target)

    if is_mobile:
        page.navigation_bar = ft.NavigationBar(
            selected_index=(
                MOBILE_DESTINATIONS.index(app.selected_screen)
                if app.selected_screen in MOBILE_DESTINATIONS else 3
            ),
            on_change=change_destination,
            destinations=[
                ft.NavigationBarDestination(icon=icon, label=label)
                for icon, label in zip(DESTINATION_ICONS, MOBILE_DESTINATIONS)
            ],
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        )
        navigation = None
    else:
        page.navigation_bar = None
        navigation = ft.Row(
            [ft.TextButton(name, on_click=nav_handler(name)) for name in [
                "Checkout", "Inventory", "Customers", "Expenses", "Reports", "Team", "Settings"
            ]] + [ft.TextButton("Sign out", on_click=app.sign_out)],
            scroll=ft.ScrollMode.AUTO,
            spacing=4,
        )

    shop = app.shop
    header_items = [
        ft.Text(shop["name"], size=20 if is_mobile else 23, weight=ft.FontWeight.BOLD),
        ft.Text(f"{app.role.title()}  ·  {shop['currency']}  ·  {shop['subscription_status'].title()}", size=12),
    ]
    if navigation is not None:
        header_items.append(navigation)
    header = ft.Column(header_items, spacing=2)

    if shop["subscription_status"] not in ("trial", "active"):
        body = ft.Column(
            [
                ft.Text("Shop access is paused", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Contact the service administrator to update this shop’s subscription."),
                ft.TextButton("Sign out", on_click=app.sign_out),
            ],
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    elif app.selected_screen == "Checkout":
        body = checkout.view(
            page, shop, app.inventory, app.customers, app.cart, app.status,
            app.receipt_text, app.search_inventory, app.add_to_cart,
            app.remove_from_cart, app.checkout, app.save_receipt, app.search_query,
        )
    elif app.selected_screen == "Inventory":
        body = management.inventory_view(
            page, shop, app.inventory, app.role, app.status, app.editing_item,
            app.save_inventory, app.edit_inventory, app.adjust_stock, app.search_inventory,
        )
    elif app.selected_screen == "Customers":
        body = management.customers_view(
            page, shop, app.customers, app.role, app.status,
            app.save_customer, app.record_debt_payment,
        )
    elif app.selected_screen == "Expenses":
        body = management.expenses_view(page, shop, app.expenses, app.role, app.status, app.save_expense)
    elif app.selected_screen == "Reports":
        body = reports.view(shop, app.sales, app.expenses, app.role, app.status, app.void_sale)
    elif app.selected_screen == "Team":
        body = management.team_view(page, app.role, app.invite_code, app.status, app.create_invite)
    elif app.selected_screen == "More":
        body = more_view(app)
    else:
        body = management.settings_view(shop, app.role, app.status, app.save_settings)

    content = ft.Column(
        [
            ft.Container(content=header, padding=ft.Padding.only(left=4, right=4, top=4, bottom=8)),
            ft.Divider(height=1),
            ft.Container(content=body, expand=True, padding=ft.Padding.symmetric(horizontal=2, vertical=6)),
        ],
        expand=True,
        spacing=4,
    )
    return ft.SafeArea(
        content=ft.Container(content=content, expand=True, padding=ft.Padding.symmetric(horizontal=12, vertical=8)),
        minimum_padding=ft.Padding.all(4),
        expand=True,
    )


def more_view(app):
    def item(label, icon, target):
        async def open_screen():
            await app.navigate(target)

        return ft.ListTile(
            leading=ft.Icon(icon),
            title=ft.Text(label),
            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
            on_click=open_screen,
        )

    return ft.Column(
        [
            ft.Text("More tools", size=21, weight=ft.FontWeight.BOLD),
            ft.Text("Reports, shop management and account"),
            ft.Card(content=ft.Column([
                item("Expenses", ft.Icons.RECEIPT_LONG, "Expenses"),
                item("Sales reports", ft.Icons.ANALYTICS, "Reports"),
                item("Team and staff", ft.Icons.GROUPS, "Team"),
                item("Shop settings", ft.Icons.SETTINGS, "Settings"),
            ], spacing=0), elevation=0),
            ft.Button(content="Sign out", on_click=app.sign_out),
        ],
        expand=True,
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )
