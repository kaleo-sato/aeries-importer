from unittest.mock import Mock, patch

from bs4 import Tag, NavigableString
from pytest import raises

from aeries_utils import (extract_gradebook_ids_from_html, GRADEBOOK_AND_TERM_TAG_NAME, GRADEBOOK_URL,
                          _get_periods_to_gradebook_and_term, )


def test_extract_gradebook_ids_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    periods = [1, 2]

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get:
        with patch('aeries_utils.BeautifulSoup', return_value=mock_beautiful_soup) as mock_beautiful_soup_create:
            with patch('aeries_utils._get_periods_to_gradebook_and_term',
                       return_value={1: 'foo', 2: 'bar'}) as mock_get_periods_to_gradebook_and_term:
                assert extract_gradebook_ids_from_html(periods=periods,
                                                       aeries_cookie='aeries-cookie') == {1: 'foo', 2: 'bar'}
                mock_requests_get.assert_called_once_with(GRADEBOOK_URL, headers={
                    'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                    'Cookie': 's=aeries-cookie'
                })
                mock_beautiful_soup_create.assert_called_once_with('my html', 'html.parser')
                mock_get_periods_to_gradebook_and_term.assert_called_once_with(periods=periods,
                                                                               beautiful_soup=mock_beautiful_soup)


def test_get_periods_to_gradebook_and_term():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find_all.return_value = [
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 1 gradebook and term'}, name='first'),
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 2 gradebook and term'}, name='second')
    ]

    mock_beautiful_soup.find.return_value.find.side_effect = [
        NavigableString(value='1 - The first class'),
        NavigableString(value='2 - The other class'),
        NavigableString(value='4 - The ignored class')
    ]

    assert _get_periods_to_gradebook_and_term(periods=[1, 2],
                                              beautiful_soup=mock_beautiful_soup) == {
        1: 'period 1 gradebook and term',
        2: 'period 2 gradebook and term'
    }


def test_get_periods_to_gradebook_and_term_invalid_class_name():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find_all.return_value = [
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 1 gradebook and term'}, name='first'),
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 2 gradebook and term'}, name='second')
    ]

    mock_beautiful_soup.find.return_value.find.side_effect = [
        NavigableString(value='1 - The first class'),
        NavigableString(value='Bad name - The other class'),
        NavigableString(value='4 - The ignored class')
    ]

    with raises(ValueError, match=r'Unexpected naming convention for Aeries class: Bad name - The other class\. '
                                  r'Expected it to start with "\[1-6\] - "'):
        _get_periods_to_gradebook_and_term(periods=[1, 2],
                                           beautiful_soup=mock_beautiful_soup)


def test_get_periods_to_gradebook_and_term():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find_all.return_value = [
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 1 gradebook and term'}, name='first'),
        Tag(attrs={GRADEBOOK_AND_TERM_TAG_NAME: 'period 2 gradebook and term'}, name='second')
    ]

    mock_beautiful_soup.find.return_value.find.side_effect = [
        NavigableString(value='1 - The first class'),
        NavigableString(value='4 - The ignored class')
    ]

    with raises(ValueError, match='Periods specified were not matched to the Aeries class gradebook.\n'
                                  'Periods wanted: 1, 2\n'
                                  r'Periods found in Aeries: 1'):
        _get_periods_to_gradebook_and_term(periods=[1, 2],
                                           beautiful_soup=mock_beautiful_soup)
