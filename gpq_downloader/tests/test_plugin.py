from unittest.mock import MagicMock, patch
from qgis.PyQt.QtWidgets import QAction
from pathlib import Path

from gpq_downloader.plugin import QgisPluginGeoParquet

def test_plugin_run_with_active_download(qgs_app, mock_iface):
    """Test run method when a download is already in progress"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.worker = MagicMock()
    plugin.worker_thread = MagicMock()
    plugin.worker_thread.isRunning.return_value = True
    
    with patch('gpq_downloader.plugin.QMessageBox.warning') as mock_warning:
        plugin.run()
        mock_warning.assert_called_once()
        assert "Download in Progress" in mock_warning.call_args[0][1]

@patch('gpq_downloader.plugin.DataSourceDialog')
def test_plugin_run_dialog_shown(mock_dialog, qgs_app, mock_iface):
    """Test run method shows dialog non-modally"""
    plugin = QgisPluginGeoParquet(mock_iface)

    # Setup mock dialog
    dialog_instance = MagicMock()
    mock_dialog.return_value = dialog_instance

    plugin.run()

    # Dialog should be shown non-modally (not exec)
    dialog_instance.show.assert_called_once()
    assert plugin.worker is None
    assert plugin.worker_thread is None

@patch('gpq_downloader.plugin.QgsSettings')
@patch('gpq_downloader.plugin.QFileDialog.getSaveFileName')
@patch('gpq_downloader.plugin.DataSourceDialog')
def test_plugin_handle_dialog_accepted(mock_dialog, mock_save_dialog, mock_settings, qgs_app, mock_iface, tmp_path):
    """Test handle_dialog_accepted with successful download setup"""
    plugin = QgisPluginGeoParquet(mock_iface)

    # Setup mock dialog
    dialog_instance = MagicMock()
    dialog_instance.get_urls.return_value = ["https://example.com/test.parquet?theme=buildings"]
    dialog_instance.overture_radio.isChecked.return_value = True
    dialog_instance.get_current_extent.return_value = None
    dialog_instance.extent_group.isChecked.return_value = False

    # Add explicit mocks for aoi properties to avoid the coordinate transformation issue
    dialog_instance.aoi_geometry = None
    dialog_instance.aoi_geometry_crs = None

    mock_dialog.return_value = dialog_instance

    # Setup mock save dialog
    output_file = str(tmp_path / "test.parquet")
    mock_save_dialog.return_value = (output_file, "GeoParquet (*.parquet)")

    # Setup mock settings
    mock_settings_instance = MagicMock()
    mock_settings.return_value = mock_settings_instance

    # Mock datetime to avoid timestamp issues
    with patch('gpq_downloader.plugin.datetime') as mock_datetime:
        mock_datetime.datetime.now.return_value.strftime.return_value = "20230101_120000"

        # Mock the process_download_queue method to avoid actual processing
        with patch.object(plugin, 'process_download_queue'):
            # Call handle_dialog_accepted directly instead of through run()
            plugin.handle_dialog_accepted(dialog_instance)

    mock_save_dialog.assert_called_once()

def test_plugin_handle_error(qgs_app, mock_iface):
    """Test error handling"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.progress_dialog = MagicMock()
    error_msg = "Test error"
    
    with patch('gpq_downloader.plugin.QMessageBox.critical') as mock_critical:
        plugin.handle_error(error_msg)
        mock_critical.assert_called_once()
        assert mock_critical.call_args[0][1] == "Error" or error_msg in mock_critical.call_args[0][1]
        plugin.progress_dialog.close.assert_called_once()

def test_plugin_update_progress(qgs_app, mock_iface):
    """Test progress updates"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.progress_dialog = MagicMock()
    
    plugin.update_progress("Test progress")
    plugin.progress_dialog.setLabelText.assert_called_once_with("Test progress")

def test_plugin_cancel_download(qgs_app, mock_iface):
    """Test download cancellation"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.worker = MagicMock()
    plugin.worker_thread = MagicMock()
    
    # Patch the cleanup_thread method to verify it's called
    with patch.object(plugin, 'cleanup_thread') as mock_cleanup:
        plugin.cancel_download()
        plugin.worker.kill.assert_called_once()
        mock_cleanup.assert_called_once()

@patch('gpq_downloader.plugin.QgsVectorLayer')
def test_plugin_load_layer_success(mock_vector_layer, qgs_app, mock_iface):
    """Test successful layer loading"""
    plugin = QgisPluginGeoParquet(mock_iface)
    
    # Setup mock layer
    mock_layer = MagicMock()
    mock_layer.isValid.return_value = True
    mock_vector_layer.return_value = mock_layer
    
    # Setup mock project
    mock_project = MagicMock()
    
    with patch('gpq_downloader.plugin.QgsProject.instance', return_value=mock_project):
        plugin.load_layer("test.gpkg")
        mock_project.addMapLayer.assert_called_once_with(mock_layer)

@patch('gpq_downloader.plugin.QgsVectorLayer')
def test_plugin_load_layer_invalid(mock_vector_layer, qgs_app, mock_iface):
    """Test loading invalid layer"""
    plugin = QgisPluginGeoParquet(mock_iface)
    
    # Setup mock layer
    mock_layer = MagicMock()
    mock_layer.isValid.return_value = False
    mock_vector_layer.return_value = mock_layer
    
    with patch('gpq_downloader.plugin.QMessageBox.critical') as mock_critical:
        plugin.load_layer("test.gpkg")
        mock_critical.assert_called_once()
        assert mock_critical.call_args[0][0] == mock_iface.mainWindow()
        assert mock_critical.call_args[0][1] == "Error" or "test.gpkg" in mock_critical.call_args[0][1]

def test_plugin_show_info(qgs_app, mock_iface):
    """Test info message display"""
    plugin = QgisPluginGeoParquet(mock_iface)
    test_message = "Test info"
    
    with patch('gpq_downloader.plugin.QMessageBox.information') as mock_info:
        plugin.show_info(test_message)
        mock_info.assert_called_once()
        assert mock_info.call_args[0][0] == mock_iface.mainWindow()
        assert mock_info.call_args[0][1] == "Success" or test_message in mock_info.call_args[0][1]

def test_plugin_initialization(qgs_app, mock_iface):
    """Test plugin initialization"""
    plugin = QgisPluginGeoParquet(mock_iface)
    assert plugin.iface == mock_iface
    assert plugin.worker is None
    assert plugin.worker_thread is None
    assert isinstance(plugin.download_dir, Path)

def test_plugin_init_gui(qgs_app, mock_iface):
    """Test initGui method"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.initGui()
    
    # Check that action was created
    assert isinstance(plugin.action, QAction)
    assert plugin.action.text() == "Download GeoParquet Data"
    
    # Check that icon was added to toolbar
    assert len(mock_iface.toolbar_icons) == 1
    assert mock_iface.toolbar_icons[0] == plugin.action

def test_plugin_unload(qgs_app, mock_iface):
    """Test plugin unload"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.initGui()  # Add the icon first
    
    # Verify icon was added
    assert len(mock_iface.toolbar_icons) == 1
    
    # Mock worker thread to not be running
    plugin.worker_thread = MagicMock()
    plugin.worker_thread.isRunning.return_value = False
    
    # Unload plugin
    plugin.unload()
    
    # Check that icon was removed
    assert len(mock_iface.toolbar_icons) == 0

@patch('gpq_downloader.plugin.QThread')
def test_plugin_cleanup_thread(mock_thread, qgs_app, mock_iface):
    """Test thread cleanup"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.worker = MagicMock()
    plugin.worker_thread = MagicMock()
    
    plugin.cleanup_thread()
    assert plugin.worker is None
    assert plugin.worker_thread is None



def test_plugin_init_gui_adds_plugins_menu(qgs_app, mock_iface):
    """Both actions appear under Plugins > GeoParquet Downloader, and unload removes them"""
    from gpq_downloader.plugin import MENU_NAME

    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.initGui()

    assert (MENU_NAME, plugin.action) in mock_iface.plugin_menu
    assert (MENU_NAME, plugin.folder_action) in mock_iface.plugin_menu
    assert plugin.folder_action.text() == "Set Download Folder..."

    plugin.unload()
    assert mock_iface.plugin_menu == []
    assert mock_iface.toolbar_icons == []


@patch('gpq_downloader.plugin.QgsSettings')
def test_plugin_uses_saved_download_dir(mock_settings, qgs_app, mock_iface, tmp_path):
    """A saved folder that still exists becomes the download folder"""
    mock_settings.return_value.value.return_value = str(tmp_path)
    plugin = QgisPluginGeoParquet(mock_iface)
    assert plugin.download_dir == tmp_path


@patch('gpq_downloader.plugin.QgsSettings')
def test_plugin_missing_saved_dir_falls_back(mock_settings, qgs_app, mock_iface, tmp_path):
    """A saved folder that has since been deleted falls back to ~/Downloads"""
    mock_settings.return_value.value.return_value = str(tmp_path / "gone")
    with patch.object(QgisPluginGeoParquet, 'default_download_dir', return_value=tmp_path / "dl"):
        plugin = QgisPluginGeoParquet(mock_iface)
    assert plugin.download_dir == tmp_path / "dl"
    assert plugin.download_dir.is_dir()


@patch('gpq_downloader.plugin.QgsSettings')
@patch('gpq_downloader.plugin.QFileDialog.getExistingDirectory')
def test_plugin_choose_download_dir_saves_setting(mock_pick, mock_settings, qgs_app, mock_iface, tmp_path):
    """Picking a folder updates the plugin and stores it in QgsSettings"""
    from gpq_downloader.plugin import DOWNLOAD_DIR_SETTING

    mock_settings.return_value.value.return_value = ""
    plugin = QgisPluginGeoParquet(mock_iface)
    mock_pick.return_value = str(tmp_path)

    assert plugin.choose_download_dir() == tmp_path
    assert plugin.download_dir == tmp_path
    mock_settings.return_value.setValue.assert_called_once()
    assert mock_settings.return_value.setValue.call_args[0][:2] == (DOWNLOAD_DIR_SETTING, str(tmp_path))


@patch('gpq_downloader.plugin.QgsSettings')
@patch('gpq_downloader.plugin.QFileDialog.getExistingDirectory', return_value="")
def test_plugin_choose_download_dir_cancel(mock_pick, mock_settings, qgs_app, mock_iface):
    """Cancelling the folder picker changes nothing"""
    mock_settings.return_value.value.return_value = ""
    plugin = QgisPluginGeoParquet(mock_iface)
    before = plugin.download_dir

    assert plugin.choose_download_dir() is None
    assert plugin.download_dir == before
    mock_settings.return_value.setValue.assert_not_called()


@patch('gpq_downloader.plugin.QFileDialog.getSaveFileName')
def test_plugin_save_dialog_starts_in_download_dir(mock_save_dialog, qgs_app, mock_iface, tmp_path):
    """The save dialog proposes a file inside the chosen download folder"""
    plugin = QgisPluginGeoParquet(mock_iface)
    plugin.download_dir = tmp_path

    dialog = MagicMock()
    dialog.get_urls.return_value = ["https://example.com/data/rivers.parquet"]
    dialog.overture_radio.isChecked.return_value = False
    dialog.sourcecoop_radio.isChecked.return_value = False
    dialog.osm_radio.isChecked.return_value = False
    dialog.get_current_extent.return_value = None
    dialog.aoi_geometry = None
    mock_save_dialog.return_value = ("", "")  # user cancels; we only check the proposal

    plugin.handle_dialog_accepted(dialog)

    proposed = Path(mock_save_dialog.call_args[0][2])
    assert proposed.parent == tmp_path
    assert proposed.name.startswith("rivers_")
