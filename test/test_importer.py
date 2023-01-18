from unittest.mock import Mock, patch, call

import pytest

from importer import run_import


@pytest.mark.xfail
def test_run_import():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('importer.get_periods_to_course_ids', return_value={1: 10, 2: 20}) as mock_get_periods_to_course_ids:
        with patch('importer.get_user_ids_to_student_emails',
                   side_effect=[{100: 'kaleoemail'}, {200: 'cindyemail'}]) as mock_get_user_ids_to_student_emails:
            assert run_import(classroom_service=mock_classroom_service,
                              periods=periods) == {100: 'kaleoemail', 200: 'cindyemail'}
            mock_get_periods_to_course_ids.assert_called_once_with(classroom_service=mock_classroom_service,
                                                                   periods=periods)
            mock_get_user_ids_to_student_emails.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                       course_id=10),
                                                                  call(classroom_service=mock_classroom_service,
                                                                       course_id=20)])
