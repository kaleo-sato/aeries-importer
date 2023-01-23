from unittest.mock import Mock, patch, call

from pytest import raises

from google_classroom_utils import _get_periods_to_course_ids, _get_user_ids_to_student_ids, \
    _get_all_published_coursework, _get_grades_for_coursework, get_submissions, AssignmentSubmissions


def test_get_submissions():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('google_classroom_utils._get_periods_to_course_ids',
               return_value={1: 10, 2: 20}) as mock_get_periods_to_course_ids:
        with patch('google_classroom_utils._get_user_ids_to_student_ids',
                   side_effect=[{100: 11, 200: 22}, {300: 33, 400: 44}]) as mock_get_user_ids_to_student_ids:
            with patch('google_classroom_utils._get_all_published_coursework',
                       side_effect=[[(1000, 'hw1'), (2000, 'hw2')],
                                    [(1000, 'hw10'), (2000, 'hw20')]]) as mock_get_all_published_coursework:
                with patch('google_classroom_utils._get_grades_for_coursework',
                           side_effect=[{100: 10, 200: 10},
                                        {100: None, 200: 5},
                                        {300: 9, 400: 9},
                                        {300: None, 400: 6}]) as mock_get_grades_for_coursework:
                    assert get_submissions(classroom_service=mock_classroom_service,
                                           periods=periods) == {
                        1: {
                            'hw1': AssignmentSubmissions(student_submissions={11: 10, 22: 10}),
                            'hw2': AssignmentSubmissions(student_submissions={11: None, 22: 5})
                        },
                        2: {
                            'hw10': AssignmentSubmissions(student_submissions={33: 9, 44: 9}),
                            'hw20': AssignmentSubmissions(student_submissions={33: None, 44: 6})
                        }}

                    mock_get_periods_to_course_ids.assert_called_once_with(classroom_service=mock_classroom_service,
                                                                           periods=periods)
                    mock_get_user_ids_to_student_ids.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                            course_id=10),
                                                                       call(classroom_service=mock_classroom_service,
                                                                            course_id=20)])
                    mock_get_all_published_coursework.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                             course_id=10),
                                                                        call(classroom_service=mock_classroom_service,
                                                                             course_id=20)])
                    mock_get_grades_for_coursework.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                          course_id=10,
                                                                          coursework_id=1000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=10,
                                                                          coursework_id=2000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=20,
                                                                          coursework_id=1000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=20,
                                                                          coursework_id=2000)])


def test_get_periods_to_course_ids():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'id': 20}]}
    assert _get_periods_to_course_ids(classroom_service=mock_classroom_service,
                                      periods=[1, 2]) == {1: 10, 2: 20}


def test_get_periods_to_course_ids_invalid_period():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'id': 20}]}

    with raises(ValueError, match=r'Period 3 is not a valid period number.'):
        _get_periods_to_course_ids(classroom_service=mock_classroom_service,
                                   periods=[1, 2, 3])


def test_get_user_ids_to_student_ids():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.return_value = {
        'students': [{'userId': 33, 'profile': {'emailAddress': 'ab12345@student.musd.org'}},
                     {'userId': 51, 'profile': {'emailAddress': 'un902934@student.musd.org'}}]
    }

    assert _get_user_ids_to_student_ids(classroom_service=mock_classroom_service, course_id=11) == {
        33: 12345,
        51: 902934
    }


def test_get_user_ids_to_student_ids_invalid_email():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.return_value = {
        'students': [{'userId': 33, 'profile': {'emailAddress': 'asdf5@gmail.com'}}]
    }

    with raises(ValueError, match=r'Student email address is in an unexpected format: asdf5@gmail.com'):
        _get_user_ids_to_student_ids(classroom_service=mock_classroom_service, course_id=11)


def test_get_all_published_coursework():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.courseWork.return_value.list.return_value.execute.return_value = {
        'courseWork': [{'id': 10, 'title': 'Biology'},
                       {'id': 20, 'title': 'Math'}]
    }

    assert _get_all_published_coursework(classroom_service=mock_classroom_service, course_id=11) == [
        (10, 'Biology'),
        (20, 'Math')
    ]


def test_get_grades_for_coursework():
    mock_classroom_service = Mock()
    (mock_classroom_service
     .courses.return_value
     .courseWork.return_value
     .studentSubmissions.return_value
     .list.return_value
     .execute.return_value) = {
        'studentSubmissions': [{'userId': 10, 'assignedGrade': 20.3},
                               {'userId': 20}]
    }

    assert _get_grades_for_coursework(classroom_service=mock_classroom_service,
                                      course_id=11,
                                      coursework_id=33) == {10: 20.3, 20: None}
