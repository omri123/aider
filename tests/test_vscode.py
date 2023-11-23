import unittest
from unittest.mock import patch
from aider import vscode
import requests


class TestClient(unittest.TestCase):
    from unittest.mock import Mock

    @patch('requests.get')
    def test_get_prefixes(self, mock_get):
        # Arrange
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = 'issue-\npr-\n'

        # Act
        titles = vscode.get_prefixes(8080)

        # Assert
        self.assertEqual(titles, ['issue-', 'pr-'])

    @patch('requests.get')
    def test_get_titles(self, mock_get):
        # Arrange
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = 'title1\ntitle2\ntitle3\n'

        # Act
        titles = vscode.get_titles(8080)

        # Assert
        self.assertEqual(titles, ['title1', 'title2', 'title3'])

    @patch('requests.get')
    def test_get_content(self, mock_get):
        # Arrange
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = 'content for title1'

        # Act
        content = vscode.get_content(8080, 'title1')

        # Assert
        self.assertEqual(content, 'content for title1')

    @patch('requests.get')
    def test_get_prefixes_timeout(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout

        # Act
        with self.assertRaises(requests.exceptions.Timeout):
            vscode.get_prefixes(8080)

    @patch('requests.get')
    def test_get_content_timeout(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout

        # Act
        with self.assertRaises(requests.exceptions.Timeout):
            vscode.get_content(8080, 'title1')

    @patch('requests.get')
    def test_get_titles_timeout(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.Timeout

        # Act
        with self.assertRaises(requests.exceptions.Timeout):
            vscode.get_titles(8080)

    @patch('requests.get')
    def test_get_titles_404(self, mock_get):
        # Arrange
        mock_get.return_value.status_code = 404

        # Act
        with self.assertRaises(Exception):
            vscode.get_titles(8080)

    @patch('requests.get')
    def test_get_content_404(self, mock_get):
        # Arrange
        mock_get.return_value.status_code = 404

        # Act
        with self.assertRaises(Exception):
            vscode.get_content(8080, 'title1')
            
