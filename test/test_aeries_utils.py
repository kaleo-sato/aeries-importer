from unittest.mock import Mock, patch, call

from bs4 import Tag, NavigableString
from pytest import raises

from aeries_utils import (extract_gradebook_ids_from_html, GRADEBOOK_AND_TERM_TAG_NAME, GRADEBOOK_URL,
                          _get_periods_to_gradebook_and_term, extract_student_ids_to_student_nums_from_html,
                          STUDENT_NUMBER_TAG_NAME, STUDENT_ID_TAG_NAME, _get_student_ids_to_student_nums,
                          extract_assignment_information_from_html, Assignment, ASSIGNMENT_DESC_TAG_NAME,
                          _get_assignment_information)


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


def test_get_periods_to_gradebook_and_term_invalid_period_num():
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


def test_extract_student_ids_to_student_nums_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get:
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils._get_student_ids_to_student_nums',
                       side_effect=[{1: 10, 2: 20},
                                    {3: 30, 4: 40}]) as mock_get_student_ids_to_student_nums:
                assert extract_student_ids_to_student_nums_from_html(periods_to_gradebook_ids={1: '123/S', 2: '234/S'},
                                                                     aeries_cookie='aeries-cookie') == {
                    1: {1: 10, 2: 20},
                    2: {3: 30, 4: 40}
                }
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/scoresByClass', headers=expected_headers),
                    call('https://aeries.musd.org/gradebook/234/S/scoresByClass', headers=expected_headers)
                ])
                mock_beautiful_soup_create.assert_has_calls([
                    call('my html', 'html.parser'),
                    call('my html', 'html.parser')
                ])
                mock_get_student_ids_to_student_nums.assert_has_calls([
                    call(beautiful_soup=mock_beautiful_soup),
                    call(beautiful_soup=mock_beautiful_soup_2)
                ])


def test_get_student_ids_to_student_nums():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find_all.return_value = [
        Tag(attrs={STUDENT_NUMBER_TAG_NAME: '1', STUDENT_ID_TAG_NAME: '10'}, name='first'),
        Tag(attrs={STUDENT_NUMBER_TAG_NAME: '2', STUDENT_ID_TAG_NAME: '20'}, name='second')
    ]

    assert _get_student_ids_to_student_nums(beautiful_soup=mock_beautiful_soup) == {10: 1, 20: 2}


def test_extract_assignment_information_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get:
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils._get_assignment_information',
                       side_effect=[
                           [Assignment(1, 'a', 10), Assignment(2, 'b', 20)],
                           [Assignment(1, 'a', 10), Assignment(3, 'c', 30)]
                       ]) as mock_get_assignment_information:
                assert extract_assignment_information_from_html(periods_to_gradebook_ids={1: '123/S', 2: '234/S'},
                                                                aeries_cookie='aeries-cookie') == {
                           1: [Assignment(1, 'a', 10), Assignment(2, 'b', 20)],
                           2: [Assignment(1, 'a', 10), Assignment(3, 'c', 30)]
                       }
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/scoresByClass', headers=expected_headers),
                    call('https://aeries.musd.org/gradebook/234/S/scoresByClass', headers=expected_headers)
                ])
                mock_beautiful_soup_create.assert_has_calls([
                    call('my html', 'html.parser'),
                    call('my html', 'html.parser')
                ])
                mock_get_assignment_information.assert_has_calls([
                    call(beautiful_soup=mock_beautiful_soup),
                    call(beautiful_soup=mock_beautiful_soup_2)
                ])


def test_get_assignment_information():
    mock_beautiful_soup = Mock()

    mock_assignment_desc_tag_1 = Mock()
    mock_assignment_desc_tag_1.get.return_value = '1 - Introductory Assignment'

    mock_assignment_tag_1 = Mock()
    mock_assignment_tag_1.find.return_value = mock_assignment_desc_tag_1
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')
    mock_assignment_tag_1.get.return_value = NavigableString(value='1')

    mock_assignment_desc_tag_2 = Mock()
    mock_assignment_desc_tag_2.get.return_value = '2 - The Next Assignment'

    mock_assignment_tag_2 = Mock()
    mock_assignment_tag_2.find.return_value = mock_assignment_desc_tag_2
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    assert _get_assignment_information(beautiful_soup=mock_beautiful_soup) == [
        Assignment(id=1,
                   name='Introductory Assignment',
                   point_total=10),
        Assignment(id=2,
                   name='The Next Assignment',
                   point_total=20)
    ]
