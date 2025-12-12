from unittest.mock import Mock, patch, call

from arrow import Arrow
from bs4 import Tag, NavigableString
from pytest import raises

from aeries_utils import (BROWSER_NAME, GRADEBOOK_AND_TERM_TAG_NAME, GRADEBOOK_URL, STUDENT_NUMBER_TAG_NAME, STUDENT_ID_TAG_NAME,
                          AeriesAssignmentData, CREATE_ASSIGNMENT_URL, AssignmentPatchData, AeriesCategory,
                          AeriesClassroomData, AeriesData)
from constants import MILPITAS_SCHOOL_CODE


def test_extract_gradebook_ids_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    periods = [1, 2]

    aeries_data = AeriesData(periods=periods, s_cookie='aeries-cookie')

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get:
        with patch('aeries_utils.BeautifulSoup', return_value=mock_beautiful_soup) as mock_beautiful_soup_create:
            with patch('aeries_utils.AeriesData._get_periods_to_gradebook_and_term',
                       return_value={1: 'foo', 2: 'bar'}) as mock_get_periods_to_gradebook_and_term:
                aeries_data.extract_gradebook_ids_from_html()
                assert aeries_data.periods_to_gradebook_ids == {1: 'foo', 2: 'bar'}
                mock_requests_get.assert_called_once_with(GRADEBOOK_URL, headers={
                    'Accept': 'application/json, text/html, application/xhtml+xml, */*',
                    'Cookie': 's=aeries-cookie'
                }, impersonate=BROWSER_NAME)
                mock_beautiful_soup_create.assert_called_once_with('my html', 'html.parser')
                mock_get_periods_to_gradebook_and_term.assert_called_once_with(beautiful_soup=mock_beautiful_soup)


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

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    assert aeries_data._get_periods_to_gradebook_and_term(beautiful_soup=mock_beautiful_soup) == {
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

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    with raises(ValueError, match=r'Unexpected naming convention for Aeries class: Bad name - The other class\. '
                                  r'Expected it to start with "\[1-6\] - "'):
        aeries_data._get_periods_to_gradebook_and_term(beautiful_soup=mock_beautiful_soup)


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

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    with raises(ValueError, match='Periods specified were not matched to the Aeries class gradebook.\n'
                                  'Periods wanted: 1, 2\n'
                                  r'Periods found in Aeries: 1'):
        aeries_data._get_periods_to_gradebook_and_term(beautiful_soup=mock_beautiful_soup)


def test_extract_student_ids_to_student_nums_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/S', 2: '234/S'}

    with (patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get):
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils.AeriesData._get_student_ids_to_student_nums',
                       side_effect=[{1: 10, 2: 20},
                                    {3: 30, 4: 40}]) as mock_get_student_ids_to_student_nums:
                aeries_data.extract_student_ids_to_student_nums_from_html()
                assert aeries_data.periods_to_student_ids_to_student_nums == {
                    1: {1: 10, 2: 20},
                    2: {3: 30, 4: 40}
                }
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME),
                    call('https://aeries.musd.org/gradebook/234/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME)
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

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    assert aeries_data._get_student_ids_to_student_nums(beautiful_soup=mock_beautiful_soup) == {10: 1, 20: 2}


def test_extract_assignment_information_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/S', 2: '234/S'}

    with (patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get):
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils.AeriesData._get_assignment_information',
                       side_effect=[
                           {'a': AeriesAssignmentData(id=1, point_total=10, category='A'),
                            'b': AeriesAssignmentData(id=2, point_total=20, category='B')},
                           {'a': AeriesAssignmentData(id=1, point_total=10, category='A'),
                            'c': AeriesAssignmentData(id=3, point_total=30, category='C')}
                       ]) as mock_get_assignment_information:
                aeries_data.extract_assignment_information_from_html()
                assert aeries_data.periods_to_assignment_information == {
                   1: {'a': AeriesAssignmentData(id=1, point_total=10, category='A'),
                       'b': AeriesAssignmentData(id=2, point_total=20, category='B')},
                   2: {'a': AeriesAssignmentData(id=1, point_total=10, category='A'),
                       'c': AeriesAssignmentData(id=3, point_total=30, category='C')}
               }
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME),
                    call('https://aeries.musd.org/gradebook/234/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME)
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
    mock_assignment_desc_tag_1.find.return_value.find_next_sibling.return_value = NavigableString(value='Performance')

    mock_assignment_tag_1 = Mock()
    mock_assignment_tag_1.find.return_value = mock_assignment_desc_tag_1
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')
    mock_assignment_tag_1.get.return_value = NavigableString(value='1')
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')

    mock_assignment_desc_tag_2 = Mock()
    mock_assignment_desc_tag_2.get.return_value = '2 - The Next Assignment'
    mock_assignment_desc_tag_2.find.return_value.find_next_sibling.return_value = NavigableString(value='Practice')

    mock_assignment_tag_2 = Mock()
    mock_assignment_tag_2.find.return_value = mock_assignment_desc_tag_2
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')


    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    assert aeries_data._get_assignment_information(beautiful_soup=mock_beautiful_soup) == {
        'Introductory Assignment': AeriesAssignmentData(id=1, point_total=10, category='Performance'),
        'The Next Assignment': AeriesAssignmentData(id=2, point_total=20, category='Practice')
    }


def test_get_assignment_information_invalid_assignment_description():
    mock_beautiful_soup = Mock()

    mock_assignment_desc_tag_1 = Mock()
    mock_assignment_desc_tag_1.get.return_value = '1 - Introductory Assignment'
    mock_assignment_desc_tag_1.find.return_value.find_next_sibling.return_value = NavigableString(value='Performance')

    mock_assignment_tag_1 = Mock()
    mock_assignment_tag_1.find.return_value = mock_assignment_desc_tag_1
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')
    mock_assignment_tag_1.get.return_value = NavigableString(value='1')

    mock_assignment_desc_tag_2 = Mock()
    mock_assignment_desc_tag_2.get.return_value = 'The Next Assignment'
    mock_assignment_desc_tag_2.find.return_value.find_next_sibling.return_value = NavigableString(value='Practice')

    mock_assignment_tag_2 = Mock()
    mock_assignment_tag_2.find.return_value = mock_assignment_desc_tag_2
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    with raises(ValueError, match=r'Unexpected format for Aeries assignment description: The Next Assignment. '
                                  'Expected it to start with "<Assignment number> - "'):
        assert aeries_data._get_assignment_information(beautiful_soup=mock_beautiful_soup)


def test_get_assignment_information_invalid_assignment_point_total():
    mock_beautiful_soup = Mock()

    mock_assignment_desc_tag_1 = Mock()
    mock_assignment_desc_tag_1.get.return_value = '1 - Introductory Assignment'
    mock_assignment_desc_tag_1.find.return_value.find_next_sibling.return_value = NavigableString(value='Performance')

    mock_assignment_tag_1 = Mock()
    mock_assignment_tag_1.find.return_value = mock_assignment_desc_tag_1
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')
    mock_assignment_tag_1.get.return_value = NavigableString(value='1')

    mock_assignment_desc_tag_2 = Mock()
    mock_assignment_desc_tag_2.get.return_value = '2 - The Next Assignment'
    mock_assignment_desc_tag_2.find.return_value.find_next_sibling.return_value = NavigableString(value='Practice')

    mock_assignment_tag_2 = Mock()
    mock_assignment_tag_2.find.return_value = mock_assignment_desc_tag_2
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value='20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    with raises(ValueError, match=r'Unexpected format for Aeries assignment point total: 20. '
                                  'Expected it to look like " : <Point total>"'):
        assert aeries_data._get_assignment_information(beautiful_soup=mock_beautiful_soup)


def test_extract_assignment_submissions_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/S', 2: '234/S'}

    with (patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get):
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils.AeriesData._get_assignment_submissions_information',
                       side_effect=[
                           {90: {200: '', 201: 'N/A', 202: '30.5', 203: 'MI'},
                            91: {200: '', 201: 'N/A', 202: '50.5', 203: 'MI'}},
                           {90: {300: '', 301: 'N/A', 302: '30.5', 303: 'MI'},
                            92: {300: '', 301: '', 302: '50.5', 303: '100'}}
                       ]) as mock_get_assignment_submissions_information:
                aeries_data.extract_assignment_submissions_from_html()
                assert aeries_data.periods_to_assignment_submissions == {
                    1: {90: {200: '', 201: 'N/A', 202: '30.5', 203: 'MI'},
                        91: {200: '', 201: 'N/A', 202: '50.5', 203: 'MI'}},
                    2: {90: {300: '', 301: 'N/A', 302: '30.5', 303: 'MI'},
                        92: {300: '', 301: '', 302: '50.5', 303: '100'}}
                }
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME),
                    call('https://aeries.musd.org/gradebook/234/S/scoresByClass', headers=expected_headers, impersonate=BROWSER_NAME)
                ])
                mock_beautiful_soup_create.assert_has_calls([
                    call('my html', 'html.parser'),
                    call('my html', 'html.parser')
                ])
                mock_get_assignment_submissions_information.assert_has_calls([
                    call(beautiful_soup=mock_beautiful_soup),
                    call(beautiful_soup=mock_beautiful_soup_2)
                ])


def test_get_assignment_submissions_information():
    mock_beautiful_soup = Mock()

    mock_submission_tag_1 = Mock()
    mock_submission_tag_1.get.side_effect = ['78', '200', 'MI']

    mock_submission_tag_2 = Mock()
    mock_submission_tag_2.get.side_effect = ['78', '201', '20.4']

    mock_submission_tag_3 = Mock()
    mock_submission_tag_3.get.side_effect = ['79', '202', '100']

    mock_submission_tag_4 = Mock()
    mock_submission_tag_4.get.side_effect = ['79', '203', '']

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_submission_tag_1,
        mock_submission_tag_2,
        mock_submission_tag_3,
        mock_submission_tag_4
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    assert aeries_data._get_assignment_submissions_information(beautiful_soup=mock_beautiful_soup) == {
        78: {200: 'MI', 201: '20.4'},
        79: {202: '100', 203: ''}
    }


def test_extract_gradebook_information_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_response.cookies = {'__RequestVerificationToken': 'request'}
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}

    with (patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get):
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils.AeriesData._get_aeries_category_information',
                       side_effect=[
                           {'Practice': AeriesCategory(id=1,
                                                       name='Practice',
                                                       weight=1.0)},
                           {'Practice': AeriesCategory(id=1,
                                                       name='Practice',
                                                       weight=0.3),
                            'Performance': AeriesCategory(id=2,
                                                          name='Performance',
                                                          weight=0.7)}
                       ]) as mock_get_category_information:
                with patch('aeries_utils.AeriesData._get_aeries_end_term_information',
                           side_effect=[
                               {'F': Arrow(year=2025, month=12, day=25)},
                               {'F': Arrow(year=2026, month=12, day=23), 'S': Arrow(year=2026, month=6, day=15)}
                          ]) as mock_get_end_term_information:
                    aeries_data.extract_gradebook_information_from_html()
                    assert aeries_data.periods_to_gradebook_information == {
                       1: AeriesClassroomData(
                           categories={'Practice': AeriesCategory(id=1,
                                                                  name='Practice',
                                                                  weight=1.0)},
                           end_term_dates={'F': Arrow(year=2025, month=12, day=25)}),
                       2: AeriesClassroomData(
                           categories={'Practice': AeriesCategory(id=1,
                                                                  name='Practice',
                                                                  weight=0.3),
                                       'Performance': AeriesCategory(id=2,
                                                                     name='Performance',
                                                                     weight=0.7)},
                           end_term_dates={'F': Arrow(year=2026, month=12, day=23),
                                           'S': Arrow(year=2026, month=6, day=15)},
                       )
                    }
                    assert aeries_data.request_verification_token == 'request'

                    mock_requests_get.assert_has_calls([
                        call('https://aeries.musd.org/gradebook/123/F/manage', headers=expected_headers, impersonate=BROWSER_NAME),
                        call('https://aeries.musd.org/gradebook/234/S/manage', headers=expected_headers, impersonate=BROWSER_NAME)
                    ])
                    mock_beautiful_soup_create.assert_has_calls([
                        call('my html', 'html.parser'),
                        call('my html', 'html.parser')
                    ])
                    mock_get_category_information.assert_has_calls([
                        call(beautiful_soup=mock_beautiful_soup),
                        call(beautiful_soup=mock_beautiful_soup_2)
                    ])
                    mock_get_end_term_information.assert_has_calls([
                        call(beautiful_soup=mock_beautiful_soup),
                        call(beautiful_soup=mock_beautiful_soup_2)
                    ])


def test_get_aeries_category_information():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find_all.return_value = [
        Tag(attrs={'data-cat-value': '1', 'value': 'Practice'}, name='first'),
        Tag(attrs={'value': '70'}, name='first_weight'),
        Tag(attrs={'data-cat-value': '2', 'value': 'Performance'}, name='second'),
        Tag(attrs={'value': '30'}, name='second_weight')
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    assert aeries_data._get_aeries_category_information(beautiful_soup=mock_beautiful_soup) == {
        'Practice': AeriesCategory(id=1,
                                   name='Practice',
                                   weight=0.7),
        'Performance': AeriesCategory(id=2,
                                      name='Performance',
                                      weight=0.3)
    }


def test_get_aeries_end_term_information():
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_term_end_date = Mock()
    mock_beautiful_soup_term_end_date.find.return_value = Tag(attrs={'value': '12/25/2023 12:00 AM'}, name='filler')
    mock_beautiful_soup.find.return_value.find_all.side_effect = [
        [Tag(attrs={'value': 'Fall'}, name='term name'), Tag(attrs={'value': 'Spring'}, name='term')],
        [mock_beautiful_soup_term_end_date, mock_beautiful_soup_term_end_date]
    ]

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')

    assert aeries_data._get_aeries_end_term_information(beautiful_soup=mock_beautiful_soup) == {
        'F': Arrow(year=2023, month=12, day=25, tzinfo='US/Pacific'),
        'S': Arrow(year=2023, month=12, day=25, tzinfo='US/Pacific')
    }


def test_create_aeries_assignment():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with (patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token')
          as mock_token):
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.post') as mock_post_request:
                mock_post_request.return_value.status_code = 200
                assert aeries_data.create_aeries_assignment(
                    gradebook_number='12345',
                    assignment_id=24,
                    assignment_name='nothing',
                    point_total=50,
                    category=AeriesCategory(name='Practice',
                                            id=1,
                                            weight=0.5),
                    end_term_date=Arrow(year=2023, month=2, day=24)
                ) == AeriesAssignmentData(id=24, point_total=50, category='Practice')

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_post_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_create_aeries_assignment_with_due_date_past_term_end_date():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=29)) as mock_arrow_now:
            with patch('aeries_utils.requests.post') as mock_post_request:
                mock_post_request.return_value.status_code = 200
                assert aeries_data.create_aeries_assignment(
                    gradebook_number='12345',
                    assignment_id=24,
                    assignment_name='nothing',
                    point_total=50,
                    category=AeriesCategory(name='Practice',
                                            id=1,
                                            weight=0.5),
                    end_term_date=Arrow(year=2023, month=1, day=25),
                ) == AeriesAssignmentData(id=24, point_total=50, category='Practice')

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_post_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_create_aeries_assignment_invalid_status_code():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.post') as mock_post_request:
                mock_post_request.return_value.status_code = 500

                with raises(ValueError, match=r'Assignment creation has unexpected status code: 500'):
                    assert aeries_data.create_aeries_assignment(
                        gradebook_number='12345',
                        assignment_id=24,
                        assignment_name='nothing',
                        point_total=50,
                        category=AeriesCategory(name='Practice',
                                                id=1,
                                                weight=0.4),
                        end_term_date=Arrow(year=2023, month=2, day=24)
                    )

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_post_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_patch_aeries_assignment():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.put') as mock_put_request:
                mock_put_request.return_value.status_code = 200
                assert aeries_data.patch_aeries_assignment(
                    gradebook_number='12345',
                    assignment_id=24,
                    assignment_name='nothing',
                    point_total=50,
                    category=AeriesCategory(name='Practice',
                                            id=1,
                                            weight=0.5),
                    end_term_date=Arrow(year=2023, month=2, day=24)
                ) == AeriesAssignmentData(id=24, point_total=50, category='Practice')

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_put_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_patch_aeries_assignment_invalid_status_code():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.put') as mock_put_request:
                mock_put_request.return_value.status_code = 500

                with raises(ValueError, match=r'Assignment update has unexpected status code: 500'):
                    assert aeries_data.patch_aeries_assignment(
                        gradebook_number='12345',
                        assignment_id=24,
                        assignment_name='nothing',
                        point_total=50,
                        category=AeriesCategory(name='Practice',
                                                id=1,
                                                weight=0.4),
                        end_term_date=Arrow(year=2023, month=1, day=25)
                    )

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_put_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_patch_aeries_assignment_with_due_date_past_term_end_date():
    expected_headers = {
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_data = {
        '__RequestVerificationToken': 'mock_token',
        'Assignment.GradebookNumber': '12345',
        'SourceGradebook.SchoolCode': MILPITAS_SCHOOL_CODE,
        'SourceGradebook.Name': 'blah',
        'Assignment.AssignmentNumber': 24,
        'Assignment.Description': 'nothing',
        'Assignment.AssignmentType': 'F',
        'Assignment.Category': 1,
        'Assignment.DateAssigned': '01/24/2023',
        'Assignment.DateDue': '01/24/2023',
        'Assignment.MaxNumberCorrect': 50,
        'Assignment.MaxScore': 50,
        'Assignment.VisibleToParents': True,
        'Assignment.ScoresVisibleToParents': True
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/F', 2: '234/S'}
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=2, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.put') as mock_put_request:
                mock_put_request.return_value.status_code = 200
                assert aeries_data.patch_aeries_assignment(
                    gradebook_number='12345',
                    assignment_id=24,
                    assignment_name='nothing',
                    point_total=50,
                    category=AeriesCategory(name='Practice',
                                            id=1,
                                            weight=0.5),
                    end_term_date=Arrow(year=2023, month=1, day=25)
                ) == AeriesAssignmentData(id=24, point_total=50, category='Practice')

                mock_token.assert_called_once_with(gradebook_number='12345')
                mock_arrow_now.assert_called_once()
                mock_put_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers,
                    impersonate=BROWSER_NAME
                )


def test_get_form_request_verification_token():
    mock_response = Mock()
    mock_response.text = 'my html'

    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value.find.return_value = Tag(attrs={'value': 'form_request_verification_token'},
                                                                  name='first')

    expected_headers = {
        'Cookie': f'__RequestVerificationToken=request_verification_token; s=s_cookie'
    }

    expected_params = {
        'gn': '12345',
        'an': 0
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.request_verification_token = 'request_verification_token'

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_request:
        with patch('aeries_utils.BeautifulSoup', return_value=mock_beautiful_soup) as mock_beautiful_soup_create:
            assert aeries_data._get_form_request_verification_token(
                gradebook_number='12345') == 'form_request_verification_token'

            mock_request.assert_called_once_with(CREATE_ASSIGNMENT_URL,
                                                 params=expected_params,
                                                 headers=expected_headers,
                                                 impersonate=BROWSER_NAME)
            mock_beautiful_soup_create.assert_called_once_with(
                'my html',
                'html.parser'
            )


def test_update_grades_in_aeries():
    assignment_patch_data = {
        'gradebook_id1': [AssignmentPatchData(student_num=99,
                                              assignment_number=123,
                                              grade=68),
                          AssignmentPatchData(student_num=99,
                                              assignment_number=124,
                                              grade=None)],
        'gradebook_id2': [AssignmentPatchData(student_num=88,
                                              assignment_number=45,
                                              grade=33),
                          AssignmentPatchData(student_num=99,
                                              assignment_number=124,
                                              grade=None)]
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, '_send_patch_request') as mock_send_patch_request:
        aeries_data.update_grades_in_aeries(assignment_patch_data=assignment_patch_data)

        mock_send_patch_request.assert_has_calls([call(gradebook_id='gradebook_id1',
                                                       assignment_number=123,
                                                       student_number=99,
                                                       grade=68),
                                                  call(gradebook_id='gradebook_id1',
                                                       assignment_number=124,
                                                       student_number=99,
                                                       grade=None),
                                                  call(gradebook_id='gradebook_id2',
                                                       assignment_number=45,
                                                       student_number=88,
                                                       grade=33),
                                                  call(gradebook_id='gradebook_id2',
                                                       assignment_number=124,
                                                       student_number=99,
                                                       grade=None)])


def test_send_patch_request():
    headers = {
        'content-type': 'application/json; charset=UTF-8',
        'cookie': 's=s_cookie'
    }

    data = {
        "SchoolCode": MILPITAS_SCHOOL_CODE,
        "GradebookNumber": '12345',
        "AssignmentNumber": 55,
        "StudentNumber": 2212,
        "Mark": 60
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')

    with patch('aeries_utils.requests.post') as mock_requests_post:
        aeries_data._send_patch_request(gradebook_id='12345/S',
                                        assignment_number=55,
                                        student_number=2212,
                                        grade=60)

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data,
            impersonate=BROWSER_NAME
        )


def test_send_patch_request_empty_grade():
    headers = {
        'content-type': 'application/json; charset=UTF-8',
        'cookie': 's=s_cookie'
    }

    data = {
        "SchoolCode": MILPITAS_SCHOOL_CODE,
        "GradebookNumber": '12345',
        "AssignmentNumber": 55,
        "StudentNumber": 2212,
        "Mark": ''
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')

    with patch('aeries_utils.requests.post') as mock_requests_post:
        aeries_data._send_patch_request(gradebook_id='12345/S',
                                        assignment_number=55,
                                        student_number=2212,
                                        grade=None)

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data,
            impersonate=BROWSER_NAME
        )


def test_send_patch_request_missing_grade():
    headers = {
        'content-type': 'application/json; charset=UTF-8',
        'cookie': 's=s_cookie'
    }

    data = {
        "SchoolCode": MILPITAS_SCHOOL_CODE,
        "GradebookNumber": '12345',
        "AssignmentNumber": 55,
        "StudentNumber": 2212,
        "Mark": 'MI'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')

    with patch('aeries_utils.requests.post') as mock_requests_post:
        aeries_data._send_patch_request(gradebook_id='12345/S',
                                        assignment_number=55,
                                        student_number=2212,
                                        grade=0)

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data,
            impersonate=BROWSER_NAME
        )


def test_extract_overall_grades_from_html():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_beautiful_soup = Mock()
    mock_beautiful_soup.find.return_value = NavigableString(value='100%')
    mock_beautiful_soup_2 = Mock()
    mock_beautiful_soup_2.find.return_value = NavigableString(value='96.65%')

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='aeries-cookie')
    aeries_data.periods_to_gradebook_ids = {1: '123/S', 2: '234/S'}
    aeries_data.periods_to_student_ids_to_student_nums = {
        1: {1: 99, 2: 88}
    }

    with (patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get):
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            assert aeries_data._extract_overall_grades_from_html(period=1) == {
                1: 100,
                2: 96.65
            }

            mock_requests_get.assert_has_calls([
                call('https://aeries.musd.org/gradebook/123/S/ScoresByStudent/99/341', headers=expected_headers, impersonate=BROWSER_NAME),
                call('https://aeries.musd.org/gradebook/123/S/ScoresByStudent/88/341', headers=expected_headers, impersonate=BROWSER_NAME)
            ])
            mock_beautiful_soup_create.assert_has_calls([
                call('my html', 'html.parser'),
                call('my html', 'html.parser')
            ])
