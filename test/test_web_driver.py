from unittest.mock import Mock, patch

from web_driver import get_aeries_cookie


def test_get_aeries_cookie():
    mock_chrome_driver_manager = Mock()
    mock_driver = Mock()

    aeries_data = Mock()
    with patch('web_driver.ChromeDriverManager',
               return_value=mock_chrome_driver_manager) as mock_chrome_driver_manager_create:
        with patch('web_driver.webdriver.Chrome', return_value=mock_driver) as mock_webdriver:
            with patch('web_driver.AeriesData', return_value=aeries_data) as mock_aeries_data_create:
                with patch('web_driver.sys') as mock_sys_exit:
                    mock_webdriver.return_value.get_cookie.return_value = {'value': 'cookie'}
                    assert get_aeries_cookie() == 'cookie'

                    mock_chrome_driver_manager_create.assert_called_once()
                    mock_chrome_driver_manager_create.return_value.install.assert_called_once()
                    mock_webdriver.return_value.get.assert_called_once_with('https://aeries.musd.org')
                    mock_webdriver.return_value.get_cookie.assert_called_once_with('s')

                    mock_aeries_data_create.assert_called_once()
                    mock_aeries_data_create.return_value.probe.assert_called_once()

                    mock_sys_exit.assert_not_called()
                    mock_webdriver.return_value.quit.assert_called_once()


def test_get_aeries_cookie_invalid_cookie():
    mock_chrome_driver_manager = Mock()
    mock_driver = Mock()

    aeries_data = Mock()
    with patch('web_driver.ChromeDriverManager',
               return_value=mock_chrome_driver_manager) as mock_chrome_driver_manager_create:
        with patch('web_driver.webdriver.Chrome', return_value=mock_driver) as mock_webdriver:
            with patch('web_driver.AeriesData', return_value=aeries_data) as mock_aeries_data_create:
                mock_aeries_data_create.return_value.probe.side_effect = AttributeError
                with patch('web_driver.sys.exit') as mock_sys_exit:
                    mock_webdriver.return_value.get_cookie.return_value = {'value': 'cookie'}

                    assert get_aeries_cookie() == 'cookie'

                    mock_chrome_driver_manager_create.assert_called_once()
                    mock_chrome_driver_manager_create.return_value.install.assert_called_once()
                    mock_webdriver.return_value.get.assert_called_once_with('https://aeries.musd.org')
                    mock_webdriver.return_value.get_cookie.assert_called_once_with('s')

                    mock_aeries_data_create.assert_called_once()
                    mock_aeries_data_create.return_value.probe.assert_called_once()

                    mock_sys_exit.assert_called_once_with(
                        'Aeries cookie is invalid. Please check if you are logged in to Aeries in your Chrome session.',
                    )
                    mock_webdriver.return_value.quit.assert_called_once()
