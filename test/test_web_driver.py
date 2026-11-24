from unittest.mock import Mock, patch, call

from web_driver import get_aeries_cookies


def create_playwright_mocks():
    mock_playwright = Mock()
    mock_browser_type = Mock()
    mock_context = Mock()
    mock_page = Mock()

    mock_playwright.chromium = mock_browser_type
    mock_browser_type.launch_persistent_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_context.cookies.return_value = [
        {"name": "s", "value": "session-cookie"},
        {"name": "AWSALB", "value": "alb-cookie"},
        {"name": "AWSALBAPP-0", "value": "app-cookie"},
    ]

    return mock_playwright, mock_context, mock_page


@patch("builtins.input")
@patch("web_driver.sync_playwright")
def test_get_aeries_cookies(mock_sync_playwright, mock_input):
    mock_playwright, mock_context, mock_page = create_playwright_mocks()
    mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

    with patch("web_driver.AERIES_URL", "https://milpitasusd.aeries.net"):
        mock_sync_playwright.return_value.__exit__.return_value = None

        with patch("web_driver.sync_playwright", return_value=mock_sync_playwright.return_value):
            cookies = get_aeries_cookies()

    assert cookies == {
        "s": "session-cookie",
        "AWSALB": "alb-cookie",
        "AWSALBAPP-0": "app-cookie",
    }

    mock_playwright.chromium.launch_persistent_context.assert_called_once_with(
        user_data_dir="./aeries_browser_profile",
        headless=False,
    )
    mock_context.new_page.assert_called_once()
    mock_page.goto.assert_called_once_with("https://milpitasusd.aeries.net")
    mock_input.assert_called_once()
    mock_context.cookies.assert_called_once_with("https://milpitasusd.aeries.net")
    mock_context.close.assert_called_once()


@patch("builtins.input")
@patch("web_driver.sync_playwright")
def test_get_aeries_cookies_closes_context_on_error(mock_sync_playwright, mock_input):
    mock_playwright, mock_context, mock_page = create_playwright_mocks()
    mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

    mock_page.goto.side_effect = Exception("Navigation failed")

    with patch("web_driver.AERIES_URL", "https://milpitasusd.aeries.net"):
        try:
            get_aeries_cookies()
            assert False, "Expected an exception"
        except Exception as exc:
            assert str(exc) == "Navigation failed"

    mock_context.close.assert_called_once()
