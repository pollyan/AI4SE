from unittest.mock import patch
from datetime import datetime

class TestProxyAPI:
    """Test cases for Proxy API"""
    
    def test_should_download_proxy_success(self, api_client):
        """Test downloading proxy package successfully"""
        with patch('os.path.exists') as mock_exists, \
             patch('backend.api.proxy.send_file') as mock_send_file:
            
            # Setup mock to return True for file existence
            mock_exists.return_value = True
            
            # Setup mock for send_file to return a dummy response
            mock_send_file.return_value = "file_content"
            
            response = api_client.get('/api/download-proxy')
            
            assert response.status_code == 200
            assert response.data.decode() == "file_content"
            mock_exists.assert_called_once()
            mock_send_file.assert_called_once()
            
            # Verify the path contains the expected filename
            call_args = mock_send_file.call_args
            assert 'intent-test-proxy.zip' in call_args[0][0]

    def test_should_return_404_when_proxy_not_found(self, api_client):
        """Test downloading proxy package when file is missing"""
        with patch('os.path.exists') as mock_exists:
            # Setup mock to return False for file existence
            mock_exists.return_value = False
            
            response = api_client.get('/api/download-proxy')
            
            assert response.status_code == 404
            assert response.json['code'] == 404
            assert "本地代理包未找到" in response.json['message']

    def test_should_handle_download_error(self, api_client):
        """Test handling error during download"""
        with patch('os.path.exists') as mock_exists, \
             patch('backend.api.proxy.send_file') as mock_send_file:
            
            mock_exists.return_value = True
            mock_send_file.side_effect = Exception("Download error")
            
            response = api_client.get('/api/download-proxy')
            
            assert response.status_code == 500
            assert response.json['code'] == 500
            assert "下载失败" in response.json['message']

    def test_should_get_proxy_version_existing_file(self, api_client):
        """Test getting proxy version when file exists"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.path.getmtime') as mock_mtime:
            
            mock_exists.return_value = True
            # Mock mtime to a specific timestamp (e.g., 2023-01-01 12:00:00)
            mock_mtime.return_value = 1672574400.0
            
            response = api_client.get('/api/proxy-version')
            
            assert response.status_code == 200
            assert response.json['code'] == 200
            assert response.json['data']['version'] == 'v1.0.0'
            # 1672574400 is 2023-01-01
            assert response.json['data']['date'] == '2023-01-01'

    def test_should_get_proxy_version_default_when_missing(self, api_client):
        """Test getting proxy version when file is missing (defaults to today)"""
        with patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = False
            
            response = api_client.get('/api/proxy-version')
            
            assert response.status_code == 200
            assert response.json['data']['version'] == 'v1.0.0'
            # Date should be today
            assert response.json['data']['date'] == datetime.now().strftime("%Y-%m-%d")

    def test_should_handle_version_check_error(self, api_client):
        """Test handling error during version check"""
        with patch('os.path.exists', side_effect=Exception("Check error")):
            
            response = api_client.get('/api/proxy-version')
            
            assert response.status_code == 500
            assert response.json['code'] == 500
            assert "获取版本信息失败" in response.json['message']
