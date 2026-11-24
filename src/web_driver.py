from playwright.sync_api import sync_playwright

AERIES_URL = "https://milpitasusd.aeries.net"

def get_aeries_cookies() -> dict:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="./aeries_browser_profile",
            headless=False
        )

        try:
            page = context.new_page()
            page.goto(AERIES_URL)

            input("Log into Aeries if necessary, then press Enter...")

            cookies = context.cookies(AERIES_URL)

            return {
                cookie["name"]: cookie["value"]
                for cookie in cookies
            }
        finally:
            context.close()
