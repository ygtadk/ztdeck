conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('VERSION', meson.project_version())
conf.set('APP_ID', application_id)
conf.set('PKGDATA_DIR', pkgdatadir)
conf.set('LOCALE_DIR', localedir)
conf.set('GETTEXT_PACKAGE', gettext_package)

configure_file(
  input: 'ztdeck.in',
  output: 'ztdeck',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

sources = [
  '__init__.py',
  'main.py',
  'client.py',
  'window.py',
  'networks.py',
  'peers.py',
  'device.py',
  'i18n.py',
  'notifications.py',
  'setup_view.py',
  'util.py',
]

install_data(sources, install_dir: pkgdatadir / 'ztdeck')
