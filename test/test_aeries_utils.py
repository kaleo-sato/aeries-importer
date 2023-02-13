from unittest.mock import Mock, patch, call

from arrow import Arrow
from bs4 import Tag, NavigableString
from pytest import raises

from aeries_utils import (extract_gradebook_ids_from_html, GRADEBOOK_AND_TERM_TAG_NAME, GRADEBOOK_URL,
                          _get_periods_to_gradebook_and_term, extract_student_ids_to_student_nums_from_html,
                          STUDENT_NUMBER_TAG_NAME, STUDENT_ID_TAG_NAME, _get_student_ids_to_student_nums,
                          extract_assignment_information_from_html, AeriesAssignmentData,
                          _get_assignment_information, create_aeries_assignment, CREATE_ASSIGNMENT_URL,
                          _get_form_request_verification_token, update_grades_in_aeries, AssignmentPatchData,
                          _send_patch_request, AeriesCategory, extract_category_information,
                          _get_aeries_category_information)
from constants import MILPITAS_SCHOOL_CODE


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
                                                       s_cookie='aeries-cookie') == {1: 'foo', 2: 'bar'}
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
                                                                     s_cookie='aeries-cookie') == {
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
                           {'a': AeriesAssignmentData(id=1, point_total=10),
                            'b': AeriesAssignmentData(id=2, point_total=20)},
                           {'a': AeriesAssignmentData(id=1, point_total=10),
                            'c': AeriesAssignmentData(id=3, point_total=30)}
                       ]) as mock_get_assignment_information:
                assert extract_assignment_information_from_html(periods_to_gradebook_ids={1: '123/S', 2: '234/S'},
                                                                s_cookie='aeries-cookie') == {
                           1: {'a': AeriesAssignmentData(id=1, point_total=10),
                               'b': AeriesAssignmentData(id=2, point_total=20)},
                           2: {'a': AeriesAssignmentData(id=1, point_total=10),
                               'c': AeriesAssignmentData(id=3, point_total=30)}
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

    assert _get_assignment_information(beautiful_soup=mock_beautiful_soup) == {
        'Introductory Assignment': AeriesAssignmentData(id=1, point_total=10),
        'The Next Assignment': AeriesAssignmentData(id=2, point_total=20)
    }


def test_get_assignment_information_invalid_assignment_description():
    mock_beautiful_soup = Mock()

    mock_assignment_desc_tag_1 = Mock()
    mock_assignment_desc_tag_1.get.return_value = '1 - Introductory Assignment'

    mock_assignment_tag_1 = Mock()
    mock_assignment_tag_1.find.return_value = mock_assignment_desc_tag_1
    mock_assignment_tag_1.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 10')
    mock_assignment_tag_1.get.return_value = NavigableString(value='1')

    mock_assignment_desc_tag_2 = Mock()
    mock_assignment_desc_tag_2.get.return_value = 'The Next Assignment'

    mock_assignment_tag_2 = Mock()
    mock_assignment_tag_2.find.return_value = mock_assignment_desc_tag_2
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value=' : 20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    with raises(ValueError, match=r'Unexpected format for Aeries assignment description: The Next Assignment. '
                                  'Expected it to start with "<Assignment number> - "'):
        assert _get_assignment_information(beautiful_soup=mock_beautiful_soup)


def test_get_assignment_information_invalid_assignment_point_total():
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
    mock_assignment_tag_2.find.return_value.find.return_value.find.return_value = NavigableString(value='20')
    mock_assignment_tag_2.get.return_value = NavigableString(value='2')

    mock_beautiful_soup.find.return_value.find_all.return_value = [
        mock_assignment_tag_1,
        mock_assignment_tag_2
    ]

    with raises(ValueError, match=r'Unexpected format for Aeries assignment point total: 20. '
                                  'Expected it to look like " : <Point total>"'):
        assert _get_assignment_information(beautiful_soup=mock_beautiful_soup)


def test_extract_category_information():
    mock_response = Mock()
    mock_response.text = 'my html'
    mock_response.cookies = {'__RequestVerificationToken': 'request'}
    mock_beautiful_soup = Mock()
    mock_beautiful_soup_2 = Mock()

    expected_headers = {
        'Accept': 'application/json, text/html, application/xhtml+xml, */*',
        'Cookie': 's=aeries-cookie'
    }

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_requests_get:
        with patch('aeries_utils.BeautifulSoup',
                   side_effect=[mock_beautiful_soup, mock_beautiful_soup_2]) as mock_beautiful_soup_create:
            with patch('aeries_utils._get_aeries_category_information',
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
                assert extract_category_information(periods_to_gradebook_ids={1: '123/S', 2: '234/S'},
                                                    s_cookie='aeries-cookie') == ({
                           1: {'Practice': AeriesCategory(id=1,
                                                          name='Practice',
                                                          weight=1.0)},
                           2: {'Practice': AeriesCategory(id=1,
                                                          name='Practice',
                                                          weight=0.3),
                               'Performance': AeriesCategory(id=2,
                                                             name='Performance',
                                                             weight=0.7)}
                       }, 'request')
                mock_requests_get.assert_has_calls([
                    call('https://aeries.musd.org/gradebook/123/S/manage', headers=expected_headers),
                    call('https://aeries.musd.org/gradebook/234/S/manage', headers=expected_headers)
                ])
                mock_beautiful_soup_create.assert_has_calls([
                    call('my html', 'html.parser'),
                    call('my html', 'html.parser')
                ])
                mock_get_category_information.assert_has_calls([
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

    assert _get_aeries_category_information(beautiful_soup=mock_beautiful_soup) == {
        'Practice': AeriesCategory(id=1,
                                   name='Practice',
                                   weight=0.7),
        'Performance': AeriesCategory(id=2,
                                      name='Performance',
                                      weight=0.3)
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

    with patch('aeries_utils._get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.post') as mock_post_request:
                mock_post_request.return_value.status_code = 200
                assert create_aeries_assignment(
                    gradebook_number='12345',
                    assignment_id=24,
                    assignment_name='nothing',
                    point_total=50,
                    category=AeriesCategory(name='Practice',
                                            id=1,
                                            weight=0.5),
                    s_cookie='s_cookie',
                    request_verification_token='request_verification_token'
                ) == AeriesAssignmentData(id=24, point_total=50)

                mock_token.assert_called_once_with(gradebook_number='12345',
                                                   s_cookie='s_cookie',
                                                   request_verification_token='request_verification_token')
                mock_arrow_now.assert_called_once()
                mock_post_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers
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

    with patch('aeries_utils._get_form_request_verification_token', return_value='mock_token') as mock_token:
        with patch('aeries_utils.Arrow.now', return_value=Arrow(year=2023, month=1, day=24)) as mock_arrow_now:
            with patch('aeries_utils.requests.post') as mock_post_request:
                mock_post_request.return_value.status_code = 500

                with raises(ValueError, match=r'Assignment creation has unexpected status code: 500'):
                    assert create_aeries_assignment(
                        gradebook_number='12345',
                        assignment_id=24,
                        assignment_name='nothing',
                        point_total=50,
                        category=AeriesCategory(name='Practice',
                                                id=1,
                                                weight=0.4),
                        s_cookie='s_cookie',
                        request_verification_token='request_verification_token'
                    )

                mock_token.assert_called_once_with(gradebook_number='12345',
                                                   s_cookie='s_cookie',
                                                   request_verification_token='request_verification_token')
                mock_arrow_now.assert_called_once()
                mock_post_request.assert_called_once_with(
                    CREATE_ASSIGNMENT_URL,
                    params={'gn': '12345', 'an': 24},
                    data=expected_data,
                    headers=expected_headers
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

    with patch('aeries_utils.requests.get', return_value=mock_response) as mock_request:
        with patch('aeries_utils.BeautifulSoup', return_value=mock_beautiful_soup) as mock_beautiful_soup_create:
            assert _get_form_request_verification_token(
                gradebook_number='12345',
                s_cookie='s_cookie',
                request_verification_token='request_verification_token'
            ) == 'form_request_verification_token'

            mock_request.assert_called_once_with(CREATE_ASSIGNMENT_URL,
                                                 params=expected_params,
                                                 headers=expected_headers)
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

    with patch('aeries_utils._send_patch_request') as mock_send_patch_request:
        update_grades_in_aeries(assignment_patch_data=assignment_patch_data,
                                s_cookie='s_cookie')

        mock_send_patch_request.assert_has_calls([call(gradebook_id='gradebook_id1',
                                                       assignment_number=123,
                                                       student_number=99,
                                                       grade=68,
                                                       s_cookie='s_cookie'),
                                                  call(gradebook_id='gradebook_id1',
                                                       assignment_number=124,
                                                       student_number=99,
                                                       grade=None,
                                                       s_cookie='s_cookie'),
                                                  call(gradebook_id='gradebook_id2',
                                                       assignment_number=45,
                                                       student_number=88,
                                                       grade=33,
                                                       s_cookie='s_cookie'),
                                                  call(gradebook_id='gradebook_id2',
                                                       assignment_number=124,
                                                       student_number=99,
                                                       grade=None,
                                                       s_cookie='s_cookie')])


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

    with patch('aeries_utils.requests.post') as mock_requests_post:
        _send_patch_request(gradebook_id='12345/S',
                            assignment_number=55,
                            student_number=2212,
                            grade=60,
                            s_cookie='s_cookie')

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data
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

    with patch('aeries_utils.requests.post') as mock_requests_post:
        _send_patch_request(gradebook_id='12345/S',
                            assignment_number=55,
                            student_number=2212,
                            grade=None,
                            s_cookie='s_cookie')

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data
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

    with patch('aeries_utils.requests.post') as mock_requests_post:
        _send_patch_request(gradebook_id='12345/S',
                            assignment_number=55,
                            student_number=2212,
                            grade=0,
                            s_cookie='s_cookie')

        mock_requests_post.assert_called_once_with(
            'https://aeries.musd.org/api/schools/341/gradebooks/12345/S/students/2212/341/scores/55',
            params={'fieldName': 'Mark'},
            headers=headers,
            json=data
        )
