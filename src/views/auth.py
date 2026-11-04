import flet as ft


def auth_screen(status, on_login, on_signup, on_google, configured):
    email = ft.TextField(label="Email", keyboard_type=ft.KeyboardType.EMAIL)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True)
    full_name = ft.TextField(label="Your name", visible=False)
    shop_name = ft.TextField(label="New shop name (leave blank to join with an invite)", visible=False)
    invite_code = ft.TextField(label="Staff invite code (optional)", visible=False)
    notice = ft.Text(status)
    login_button = ft.Button(content="Sign in")
    signup_button = ft.Button(content="Create account", visible=False)
    google_button = ft.OutlinedButton(content="Continue with Google", visible=configured)
    switch_button = ft.TextButton(content="New here? Create an account")
    back_button = ft.TextButton(content="Back to sign in", visible=False)

    async def login():
        await on_login(email.value, password.value)

    async def signup():
        await on_signup(email.value, password.value, full_name.value, shop_name.value, invite_code.value)

    async def google_sign_in():
        await on_google(full_name.value, shop_name.value, invite_code.value, signup_button.visible)

    def show_signup():
        full_name.visible = True
        shop_name.visible = True
        invite_code.visible = True
        login_button.visible = False
        signup_button.visible = True
        switch_button.visible = False
        back_button.visible = True
        notice.value = "Create a shop-owner account, or leave the shop name blank and enter a staff invite code."
        content.update()

    def show_login():
        full_name.visible = False
        shop_name.visible = False
        invite_code.visible = False
        login_button.visible = True
        signup_button.visible = False
        switch_button.visible = True
        back_button.visible = False
        notice.value = status
        content.update()

    login_button.on_click = login
    signup_button.on_click = signup
    google_button.on_click = google_sign_in
    switch_button.on_click = show_signup
    back_button.on_click = show_login

    content = ft.Column(
        [
            ft.Text("Noble POS Cloud", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Connected point of sale for shops in Tanzania"),
            ft.Text(
                "Supabase is not connected. Configure src/config.py and run src/core/schema.sql before accounts can be used.",
                visible=not configured,
            ),
            notice,
            email,
            password,
            full_name,
            shop_name,
            invite_code,
            login_button,
            signup_button,
            google_button,
            ft.Text(
                "Google sign-in does not automatically share the phone number on your Google account.",
                size=12,
                visible=configured,
            ),
            switch_button,
            back_button,
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
    return ft.SafeArea(content=content, minimum_padding=ft.Padding.all(16), expand=True)


def onboarding_screen(status, default_name, on_create):
    name = ft.TextField(label="Shop name", value=default_name)
    tax = ft.TextField(label="Tax rate (%)", value="0")

    async def create():
        await on_create(name.value, tax.value)

    return ft.SafeArea(
        content=ft.Column(
            [
                ft.Text("Set up your shop", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(status),
                name,
                tax,
                ft.Button(content="Create shop", on_click=create),
            ],
            expand=True,
        ),
        minimum_padding=ft.Padding.all(16),
        expand=True,
    )
