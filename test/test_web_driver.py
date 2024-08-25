from unittest.mock import Mock, patch

from web_driver import get_aeries_cookie


def test_get_aeries_cookie():
    mock_chrome_driver_manager = Mock()
    mock_driver = Mock()
    with patch('web_driver.ChromeDriverManager',
               return_value=mock_chrome_driver_manager) as mock_chrome_driver_manager_create:
        with patch('web_driver.webdriver.Chrome', return_value=mock_driver) as mock_webdriver:
            mock_webdriver.return_value.get_cookie.return_value = {'value': 'cookie'}
            assert get_aeries_cookie() == 'cookie'

            mock_chrome_driver_manager_create.assert_called_once()
            mock_chrome_driver_manager_create.return_value.install.assert_called_once()
            mock_webdriver.return_value.get.assert_called_once_with('https://aeries.musd.org')
            mock_webdriver.return_value.get_cookie.assert_called_once_with('s')
            mock_webdriver.return_value.quit.assert_called_once()
